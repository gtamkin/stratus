from flask import request, Blueprint, make_response
from stratus_endpoint.handler.base import Task, TaskResult
from stratus.handlers.client import StratusClient
import pickle, ctypes, json, requests, flask, os
from jinja2 import Environment, PackageLoader, select_autoescape
from stratus.handlers.app import StratusAppBase
from typing import *
from stratus.handlers.rest.app import RestAPIBase
HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATES = os.path.join(HERE, "templates")

class RestAPI(RestAPIBase):
    debug = False

    def __init__( self, name: str, app: StratusAppBase, **kwargs ):
        RestAPIBase.__init__( self, name, app, **kwargs )
        self.jenv = Environment( loader=PackageLoader( 'stratus.handlers.rest.api.wps',  "templates" ), autoescape=select_autoescape(['html','xml']) )
        self.templates = {}
        self.templates['execute_response'] = self.jenv.get_template('execute_response.xml')
        self.dapRoute = kwargs.get( "dapRoute", None )

    def parseDatainputs(self, datainputs: str) -> Dict:
        if datainputs is None: return {}
        raw_datainputs = ctypes.create_string_buffer(datainputs.strip())
        if raw_datainputs[0] == "[":
            assert raw_datainputs[-1] == "]", "Datainputs format error: missing external brackets: " + raw_datainputs
            raw_datainputs[0] = "{"
            raw_datainputs[-1] = "}"
        return json.loads(raw_datainputs)

    def processRequest( self, requestDict: Dict ) -> flask.Response:
        if self.debug: self.logger.info(f"Processing Request: '{str(requestDict)}'")
        current_tasks = self.app.processWorkflow(requestDict)
        if self.debug: self.logger.info("Current tasks: {} ".format(str(list(current_tasks.items()))))
        for task in current_tasks.values(): self.addTask( task )
        return self.executeResponse( requestDict )

    def executeResponse(self, response: Dict ) -> flask.Response:
        status = response["status"]
        responseXml = None
        if status == "executing":
            responseXml = self.getStatusXml( "ProcessStarted", response["message"] )
        elif status == "completed":
            responseXml = self.getStatusXml( "ProcessSucceeded", response["message"] )
        elif status == "idle":
            responseXml = self.getStatusXml("ProcessAccepted", response["message"])
        elif status == "error":
            responseXml = self.getStatusXml("ProcessFailed", response["message"], response["rid"],  False)
        return flask.Response( response=responseXml, status=400, mimetype="application/xml" )

    def getStatusXml(self, status: str, message: str, rid: str, addDataRefs = True ) -> str :
        status = dict( tag=status, mesage=message )
        route = request.path
        print ( route )
        url = dict( status=f"{route}/status?id={rid}" )
        if addDataRefs:
            url['file'] = f"{route}/file?id={rid}"
            if self.dapRoute is not None:
                url['dap'] = f"{self.dapRoute}/{rid}.nc"
        return self.templates['execute_response'].render( dict(status=status, url=url) )

    def getCapabilities(self, id: str ) -> flask.Response:
        responseXml = ""
        return flask.Response(response=responseXml, status=400, mimetype="application/xml" )

    def describeProcess(self, id: str ) -> flask.Response:
        responseXml = ""
        return flask.Response(response=responseXml, status=400, mimetype="application/xml" )

    def _addRoutes(self, bp: Blueprint):
        self.logger.info( "Adding WPS routes" )
        @bp.route('/cwt', methods=['GET'] )
        def exe():
            requestArg = request.args.get("request", None)
            if requestArg == "Execute":
                datainputs = request.args.get("datainputs", None)
                inputsArg = self.parseDatainputs( datainputs )
                return self.processRequest( inputsArg )
            elif requestArg == "GetCapabilities":
                id = request.args.get("id",  None )
                return self.getCapabilities(id)
            elif requestArg == "DescribeProcess":
                id = request.args.get("id",  None )
                return self.describeProcess(id)
            else:
                return self.executeResponse( dict( status='error', message ="Illegal request type: " + requestArg ) )

        @bp.route('/status', methods=['GET'])
        def status():
            rid = self.getParameter( "rid", None, False)
            statusMap = self.getStatus(rid)
            if self.debug: self.logger.info( "Status Map: " + str(statusMap) )
            return self.jsonResponse( statusMap )

        @bp.route('/file', methods=['GET'])
        def result():
            rid = self.getParameter("rid")
            task: Task = self.tasks.get( rid, None )
            assert task is not None, f"Can't find task for rid {rid}, current tasks: {str(list(self.tasks.keys()))}"
            result: Optional[TaskResult] = task.getResult()
            if result is None:
                return self.jsonResponse( dict(status="executing", id=task.rid) )
            else:
                response = make_response( pickle.dumps( result ) )
                response.headers.set('Content-Type', 'application/octet-stream')
                response.headers.set('Content-Class', 'xarray-dataset' )
                self.removeTask( rid )
                return response




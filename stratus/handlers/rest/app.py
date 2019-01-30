from connexion.resolver import Resolver
from connexion.operations import AbstractOperation
import os, traceback
from flask import Flask, Response
import connexion, json, logging
from stratus.handlers.base import Handlers
from functools import partial
from stratus.util.config import Config, StratusLogger
from flask_sqlalchemy import SQLAlchemy

class StratusResolver(Resolver):

    def __init__(self  ):
        Resolver.__init__( self, self.function_resolver )

    def resolve_operation_id( self, operation: AbstractOperation ) -> str:
        return '{}:{}'.format( self.api, operation.operation_id )

    def function_resolver( self, operation_id: str ) :
        return partial( Handlers.processRequest, operation_id )

class StratusApp:
    HERE = os.path.dirname(__file__)
    SETTINGS = os.path.join( HERE, 'settings.ini')

    def __init__(self):
        self.logger = StratusLogger.getLogger()
        self.app = connexion.FlaskApp("stratus", specification_dir='handlers/rest/api/', debug=True )
        self.app.add_error_handler( 500, self.render_server_error )
        self.app.app.register_error_handler( TypeError, self.render_server_error )
        settings = os.environ.get( 'STRATUS_SETTINGS', self.SETTINGS )
        config_file = Config(settings)
        flask_parms = config_file.get_map('flask')
        flask_parms[ 'SQLALCHEMY_DATABASE_URI' ] = flask_parms['DATABASE_URI']
        self.app.app.config.update( flask_parms )
        self.parms = config_file.get_map('stratus')
        rest_api = self.getParameter( 'REST_API' )
        self.db = SQLAlchemy( self.app.app )
        self.app.add_api( rest_api + ".yaml", resolver=StratusResolver() )

    def run(self):
        port = self.getParameter( 'PORT', 5000 )
        self.db.create_all( )
        return self.app.run( int( port ) )

    def getParameter(self, name: str, default = None ) -> str:
        parm = self.parms.get( name, default )
        if parm is None: raise Exception( "Missing required stratus parameter in settings.ini: " + name )
        return parm

    @staticmethod
    def render_server_error( ex: Exception ):
        print( str( ex ) )
        traceback.print_exc()
        return Response(response=json.dumps({ 'message': getattr(ex, 'message', repr(ex)), "code": 500, "id": "", "status": "error" } ), status=500, mimetype="application/json")


app = StratusApp()

if __name__ == "__main__":
    app.run()
import six
from typing import List, Dict, Any, Sequence, BinaryIO, TextIO, ValuesView, Optional

class HtmlCodec:
    def marshal(self, value, **kwargs):
        return value

    def unmarshal(self, data, **kwargs):
        if isinstance(data, six.binary_type):
            data = data.decode('utf-8')
        return { "message": data, "code": 0 }

def s2b( s: str ):
    return s.encode( 'utf-8'  )

def b2s( b: bytearray ):
    return b.decode( 'utf-8'  )

def ia2s( array: Sequence[int] ) -> str:
    return str(array).strip("[]")

def sa2s( array: Sequence[str] ) -> str:
    return ",".join(array)

def m2s( metadata: Dict[str,str] ) -> str:
    items = [ ":".join(item) for item in metadata.items() ]
    return ";".join(items)
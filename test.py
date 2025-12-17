import struct
import sys
from PyQt5.QAxContainer import QAxWidget

print(sys.executable, struct.calcsize('P')*8)

'''
Created on Mar 15, 2017

@author: howie

FEL commands in Python
'''
from struct import unpack, pack, unpack_from
from collections import namedtuple

FEL_DOWNLOAD = 0x101 # // (Write data to the device)
FEL_RUN = 0x102 # (Execute code)
FEL_UPLOAD  = 0x103# (Read data from the device)
FEL_VERSION = 0x001

AW_USB_READ = 0x11
AW_USB_WRITE = 0x12

USB_CMD_LEN = 0x0c000000 #from doc: 0xC
USB_REQUEST_FORMAT = '<4sIIIHI10x'

FEL_REQUEST_FORMAT = '<III4x'
FEL_VERSION_SIZE = 32

RESPONSE_BUFFER_LENGTH = 13 # AWUSBResponse
STATUS_BUFFER_LENGTH = 8; # AWFELStatusResponse
AWUS_RESPONSE = "AWUS" # used by aw_read_usb_response
AWUC = "AWUC"

FEL_VERSION_FORMAT = '<8sIIHccI8x'
FelVersionStruct = namedtuple('FelVersion', 'signature soc_id unknown0a protocol unknown12 unknown13 scratchpad')

# Other SOC's can be supported by adding their swap buffer info from fel.c
a10_a13_a20_sram_swap_buffers = [
    # 0x1C00-0x1FFF (IRQ stack) 
    { 'buf1': 0x01C00, 'buf2': 0xA400, 'size': 0x0400},
    # 0x5C00-0x6FFF (Stack) */
    { 'buf1': 0x05C00, 'buf2': 0xA800, 'size': 0x1400 },
    # 0x7C00-0x7FFF (Something important) 
    { 'buf1': 0x07C00, 'buf2': 0xBC00, 'size': 0x0400 },
    # End sentinel 
    { 'buf1': 0, 'buf2': 0, 'size': 0 }
];

SRAM_INFO_MAP = {
     # Allwinner A13
    0x1625: {
        'soc_id': 0x1625,
        'spl_addr': 0,
        'scratch_addr': 0x1000,
        'thunk_addr': 0xA200,
        'thunk_size': 0x200,
        'needs_l2en': True,
        'mmu_tt_addr': 0,
        'sid_addr': 0x01C23800,
        'rvbar_reg': 0,
        'swap_buffers': a10_a13_a20_sram_swap_buffers
    }
}

# Low level calls
def _usbRequest(usb, requestType, length):
    requestBuffer = pack(USB_REQUEST_FORMAT, AWUC,0,length,USB_CMD_LEN,requestType,length)
    return usb.write(requestBuffer)

def _usbResponse(usb):
    response = usb.readString(RESPONSE_BUFFER_LENGTH)
    return response.startswith(AWUS_RESPONSE)

def _status(usb):
    return _usbRead(usb,STATUS_BUFFER_LENGTH)

def _usbWrite(usb, data):
    dataLength = len(data)
    _usbRequest(usb, AW_USB_WRITE, dataLength)
    usb.write(data,dataLength)
    return _usbResponse(usb)

def _usbRead(usb, length):
    _usbRequest(usb, AW_USB_READ, length)
    data = usb.read(length)
    _usbResponse(usb)
    return data

def _request(usb, requestType, address = 0, length = 0):
    requestBuffer = pack(FEL_REQUEST_FORMAT, requestType, address ,length)
    return _usbWrite(usb,requestBuffer)

def dump(buf):
    res = ""
    for c in buf:
        res += "{:02x}".format(ord(c))
    return res

def _readl_n(usb, address, count, scratch_addr):
    arm_code = [
        0xe59f0010,
        0xe5901000,
        0xe58f100c,
        0xe2800004,
        0xe58f0000,
        0xe12fff1e,
        address
    ]
    codeBuffer = pack('<' + str(len(arm_code)) + 'I', *arm_code)
    write(usb, codeBuffer, scratch_addr)
    
    result = []
    for _ in xrange(count):
        exe(usb, scratch_addr)
        val = read(usb, scratch_addr + 28, 4)
        intVal = unpack_from('<I',val)[0]
        result.append(intVal)
    
    return result
#####################################################################
def read(usb, address, length):
    _request(usb, FEL_UPLOAD, address, length)
    data = _usbRead(usb, length)
    _status(usb)
    return data

def write(usb, data, address):
    _request(usb, FEL_DOWNLOAD, address, len(data))
    _usbWrite(usb,data)
    return _status(usb)

def exe(usb, address):
    _request(usb, FEL_RUN, address)
    return _status(usb)
    
####################################################################    
def getVersion(usb):
    _request(usb,FEL_VERSION)
    data = _usbRead(usb, FEL_VERSION_SIZE)
    version = FelVersionStruct._make(unpack(FEL_VERSION_FORMAT, data))
    fixed_soc_id = (version.soc_id >> 8) & 0xFFFF
    version = version._replace(soc_id=fixed_soc_id)
    _status(usb)
    return version

def getSid(usb):
    version = getVersion(usb)
    sram_info = SRAM_INFO_MAP[version.soc_id]
    return _readl_n(usb, int(sram_info['sid_addr']), 4, int(sram_info['scratch_addr']))

def getSerialNumber(usb):
    sid = getSid(usb)
    serial = '{:08x}{:08x}'.format(sid[0],sid[3])
    return serial

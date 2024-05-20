'''
A Python port of KUKA VarProxy client (OpenShowVar).

Based on py_openvarproxy
Slightly modified by the BYR0034@VSB.CZ, and PIE0073@VSB.CZ
'''

import struct
import random
import socket

__version__ = '1.1.8'
ENCODING = 'UTF-8'

class openshowvar(object):
    """Connector class for C3 Bridge
    """    

    def __init__(self, ip: str, port: int):
        """Connector class for C3 Bridge

        Args:
            ip (str): Robot's IPv4
            port (int): C3 Bridge port. Usually 7000
        """        

        self.ip = ip
        self.port = port
        self.msg_id = random.randint(1, 100)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.retry = 0
        self.retry_limit = 5
        try:
            self.sock.connect((self.ip, self.port))
        except socket.error:
            pass

    def test_connection(self) -> bool:
        """Tests the connection to the robot

        Returns:
            bool: The robot is online
        """        

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            ret = sock.connect_ex((self.ip, self.port))
            return ret == 0
        except socket.error:
            print('socket error')
            return False

    can_connect = property(test_connection)

    def read(self, var: str, debug=True) -> bytes | None:
        """Reads data from the robot

        Args:
            var (str): The variable to read in KRL syntax
            debug (bool, optional): Prints the raw request result in the terminal. Defaults to True.

        Raises:
            Exception: 'Var name is array string'

        Returns:
            bytes | None: The read bytes. None if the connection is broken
        """             

        try:
            if not isinstance(var, str):
                raise Exception('Var name is array string')
            else:
                self.varname = var.encode(ENCODING)
            return self._read_var(debug)
        except:
            self.retry += 1
            if self.retry != self.retry_limit:
                print('read error, ' + str(self.retry) + ' - try')
                self.read(var)
            else:
                print('read error, socket closed')
                self.retry = 0
                self.close()
                return

    def write(self, var: str, value: str, debug=False) -> bool:
        """Assigns a value to a variable

        Args:
            var (str): The variable to write
            value (str): The value to assign to the variable
            debug (bool, optional): Reads and shows the written variable in the terminal. Defaults to False.

        Raises:
            Exception: 'Var name and its value should be string'

        Returns:
            bool: The value has been written
        """        

        if not (isinstance(var, str) and isinstance(value, str)):
            raise Exception('Var name and its value should be string')
        self.varname = var.encode(ENCODING)
        self.value = value.encode(ENCODING)
        return self._write_var(debug)

    def _read_var(self, debug: bool) -> bytes | None:
        """Raw reading procedure to get data from the C3 bridge

        Args:
            debug (bool): Prints the read value

        Returns:
            bytes | None: The read value
        """        

        req = self._pack_read_req()
        self._send_req(req)
        _value = self._read_rsp(debug)
        if debug:
            print(_value)
        return _value

    def _write_var(self, debug: bool) -> bytes | None:
        """Raw writing procedure to send data to the C3 bridge

        Args:
            debug (bool): Read and print the written value

        Returns:
            bytes | None: The written value if in debug mode, else None
        """        
        
        req = self._pack_write_req()
        self._send_req(req)

        if debug:
            _value = self._read_rsp(debug)
            print(_value)
            return _value

    def _send_req(self, req: bytes):
        """Sends bytes to the C3 bridge and reads the response. The current 
        character limit is set to 8192.

        Args:
            req (bytes): The bytes to write to the C3 Bridge
        """        

        self.rsp = None
        self.sock.sendall(req)
        self.rsp = self.sock.recv(8192)

    def _pack_read_req(self) -> bytes:
        """Packs the current request to the C3 Bridge format

        Returns:
            bytes: The encoded data
        """        

        var_name_len = len(self.varname)
        flag = 0
        req_len = var_name_len + 3

        return struct.pack(
            '!HHBH'+str(var_name_len)+'s',
            self.msg_id,
            req_len,
            flag,
            var_name_len,
            self.varname
            )

    def _pack_write_req(self) -> bytes:
        """Packs the current request to the C3 Bridge format

        Returns:
            bytes: The encoded data
        """   

        var_name_len = len(self.varname)
        flag = 1
        value_len = len(self.value)
        req_len = var_name_len + 3 + 2 + value_len

        return struct.pack(
            '!HHBH'+str(var_name_len)+'s'+'H'+str(value_len)+'s',
            self.msg_id,
            req_len,
            flag,
            var_name_len,
            self.varname,
            value_len,
            self.value
            )

    def _read_rsp(self, debug=False) -> bytes | None:
        """Reads the response to the current request

        Args:
            debug (bool, optional): Prints the raw result to the terminal. Defaults to False.

        Returns:
            bytes | None: The decoded response in bytes, None if no response is available.
        """        

        if self.rsp is None: return None
        var_value_len = len(self.rsp) - struct.calcsize('!HHBH') - 3
        result = struct.unpack('!HHBH'+str(var_value_len)+'s'+'3s', self.rsp)
        _msg_id, body_len, flag, var_value_len, var_value, isok = result
        if debug:
            print('[DEBUG]', result)
        if result[-1].endswith(b'\x01') and _msg_id == self.msg_id:
            self.msg_id = (self.msg_id + 1) % 65536  # format char 'H' is 2 bytes long
            return var_value

    def close(self):
        """Closes the socket
        """        
        self.sock.close()


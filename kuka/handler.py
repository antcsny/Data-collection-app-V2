from .kukavarproxy import openshowvar

class KUKA_Handler:
    def __init__(self, ipAddress, port):
        self.connected = False
        self.ipAddress = ipAddress
        self.port = port
        self.client = None

    def KUKA_Open(self):
        if self.connected == False:
            self.client = openshowvar(self.ipAddress, self.port)
            res = self.client.can_connect

            if res == True:
                print('Connection is established!')
                self.connected = True
                return True
            else:
                print('Connection is broken! Check configuration or restart C3_Server at KUKA side.')
                self.connected = False
                return False
        else:
            print('Connection is ready!')

    def KUKA_ReadVar(self, var):
        if self.connected:
            res = self.client.read(var, debug=False)
            if res == b'TRUE':
                return True
            elif res == b'FALSE':
                return False
            else:
                return res
        else:
            return False

    def KUKA_WriteVar(self, var, value):
        if self.connected:
            self.client.write(var, str(value))
            return True
        else:
            return False

    def KUKA_Close(self):
        if self.connected == True:
            self.client.close()
            self.connected = False
            return True

        else:
            return False

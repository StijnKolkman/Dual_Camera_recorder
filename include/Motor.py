from ctypes import *
from enum import IntEnum
# sleep function
import time
import os

class MotorMode(IntEnum):
    ProfilePosition = 1
    ProfileVelocity = 3
    Homing = 6
    InterpolatedPosition = 7
    Position = -1
    Velocity = -2
    Current = -3
    MasterEncoder = -5
    StepDirection = -6


class Motor:
    def __init__(self, NodeID, USBID):

        path= os.path.dirname(os.path.abspath(__file__))+'/EposCmd64.dll'
        cdll.LoadLibrary(path)
        self.epos=CDLL(path)

        # motor connection variables
        self.keyhandle = 0
        self.NodeID = NodeID
        self.USBID = USBID

        # return variables
        self.ret = 0
        self.pErrorCode = c_uint()
        self.pDeviceErrorCode = c_uint()

    def WaitAcknowledged(self):
        ObjectIndex=0x6041
        ObjectSubindex=0x0
        NbOfBytesToRead=0x02
        pNbOfBytesRead=c_uint()
        pData=c_uint()

        # Setpoint Acknowledged
        Mask_Bit12=0x1000
        Bit12=0
        i=0

        while True:
            # Read Statusword
            self.ret=self.epos.VCS_GetObject(self.keyhandle, self.NodeID, ObjectIndex, ObjectSubindex, byref(pData), NbOfBytesToRead, byref(pNbOfBytesRead), byref(self.pErrorCode) )
            Bit12=Mask_Bit12&pData.value

            # Timed out
            if i>20:
                return 0
                break

            if Bit12==Mask_Bit12:
                time.sleep(1)
                i+=1

            # Bit12 reseted = new profile started
            else:
                return 1
                break

    def GetPosition(self):
        # CANopen Object: Position Actual Value
        ObjectIndex=0x6064
        ObjectSubIndex=0x00
        NbOfBytesToRead=0x04
        # DWORD
        NbOfBytesRead=c_uint()
        # 0x6064 => INT32
        pData=c_int()

        self.ret=self.epos.VCS_GetObject(self.keyhandle, self.NodeID, ObjectIndex, ObjectSubIndex, byref(pData), NbOfBytesToRead, byref(NbOfBytesRead), byref(self.pErrorCode) )

        if self.ret==1:
            print('Position Actual Value: %d [inc]' % pData.value)
            return 1
        else:
            print('GetObject failed')
            return 0
        
    def GetPositionIs(self):
        pPositionIs=c_long()

        ret=self.epos.VCS_GetPositionIs(self.keyhandle, self.NodeID, byref(pPositionIs), byref(self.pErrorCode) )

        if ret==1:
            print('Position Actual Value: %d [inc]' % pPositionIs.value)
            return 1
        else:
            print('GetPositionIs failed')
            return 0    

    def OpenCommunication(self):
        print('Opening Port...')
        self.keyhandle=self.epos.VCS_OpenDevice(b'EPOS4', b'MAXON SERIAL V2', b'USB', bytes(f'USB{self.USBID}',"utf-8"), byref(self.pErrorCode) )

        if self.keyhandle != 0:
            print('keyhandle: %8d' % self.keyhandle)

            # Verify Error State of EPOS4
            self.ret=self.epos.VCS_GetDeviceErrorCode(self.keyhandle, self.NodeID, 1, byref(self.pDeviceErrorCode), byref(self.pErrorCode) )
            print('Device Error: %#5.8x' % self.pDeviceErrorCode.value )            

        else:
            print('Could not open Com-Port')
            print('keyhandle: %8d' % self.keyhandle)
            print('Error Openening Port: %#5.8x' % self.pErrorCode.value)
        
    def EnableMotor(self):
            # Device Error Evaluation
            if self.pDeviceErrorCode.value==0:
                self.ret=self.epos.VCS_SetEnableState(self.keyhandle, self.NodeID, byref(self.pErrorCode) )
                print('Device Enabled')
            else:
                print('epos4 is in Error State: %#5.8x' % self.pDeviceErrorCode.value)
                print('epos4 Error Description can be found in the epos4 Fimware Specification')

    def DisableMotor(self):
            self.ret=self.epos.VCS_SetDisableState(self.keyhandle, self.NodeID, byref(self.pErrorCode) )
            print('Device Disabled')

    def CloseCommunication(self):
            self.ret=self.epos.VCS_CloseDevice(self.keyhandle, byref(self.pErrorCode) )
            print('Error Code Closing Port: %#5.8x' % self.pErrorCode.value)
    
    # Setting operation mode
    def SetOperationMode(self, mode: MotorMode):
        self.ret = self.epos.VCS_SetOperationMode(self.keyhandle, self.NodeID, mode.value, byref(self.pDeviceErrorCode))
        if self.ret != 0:
            self.mode = mode


    # Velocity Profile Mode commands
    def SetVelocityProfile(self,acceleration,deceleration):
        self.ret=self.epos.VCS_SetVelocityProfile(self.keyhandle, self.NodeID, acceleration, deceleration, byref(self.pErrorCode) )
        self.SetOperationMode(MotorMode.ProfileVelocity)

    def RunSetVelocity(self,velocity):
        if self.mode == MotorMode.ProfileVelocity:
            self.ret=self.epos.VCS_MoveWithVelocity(self.keyhandle, self.NodeID, velocity, byref(self.pErrorCode))


    # Position Mode commands
    def SetPositionMust(self, position):
        if self.mode == MotorMode.Position:
            self.ret = self.epos.VCS_SetPositionMust(self.keyhandle, self.NodeID, position, byref(self.pDeviceErrorCode))    
    

    # Position Profile Mode commands
    def SetPositionProfile(self, velocity, acceleration, deceleration):
        self.ret = self.epos.VCS_SetPositionProfile(self.keyhandle, self.NodeID, velocity, acceleration, deceleration, byref(self.pDeviceErrorCode))
        self.SetOperationMode(MotorMode.ProfilePosition)
    
    def SetPosition(self, position, absolute: bool, immediately: bool):
        if self.mode == MotorMode.ProfilePosition:
            self.ret = self.epos.VCS_MoveToPosition(self.keyhandle, self.NodeID, position, absolute, immediately, byref(self.pDeviceErrorCode))


if __name__ == "__main__":
    mode = MotorMode.ProfilePosition
    print(mode.value)

    rpm1 = Motor(1,0)
    rpm1.OpenCommunication()

    if rpm1.keyhandle !=0:
        rpm1.EnableMotor()
        # rpm1.SetVelocityProfile(8000,8000)
        # rpm1.GetPositionIs()
        # rpm1.RunSetVelocity(int((26.0/7.0)*60.0*1))
        # time.sleep(1)
        # rpm1.GetPositionIs()
        # rpm1.RunSetVelocity(0)
        # time.sleep(1)
        # rpm1.RunSetVelocity(-int((26.0/7.0)*60.0*2))
        # time.sleep(1)
        # rpm1.GetPositionIs()

        # Test Position mode
        rpm1.SetOperationMode(MotorMode.Position)
        rpm1.SetPositionProfile(100,8000,8000)
        rpm1.SetPosition(int((26.0/7.0)*2000),False,False) # 1 rotation, gearbox 26/7 and 2000 encoder counts per rotation
        time.sleep(3)
        rpm1.GetPositionIs()

        rpm1.DisableMotor()
        rpm1.CloseCommunication()
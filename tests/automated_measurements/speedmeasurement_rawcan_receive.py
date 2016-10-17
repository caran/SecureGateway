#######################################################################################
####                       Save incoming CAN frames to text file                    ###
### Intended for measuring the speed of the Python implementation of SocketCAN etc. ###
#######################################################################################

import socket
import struct
import sys
import time

assert sys.version_info >= (3, 3, 0), "Python version 3.3 or later required!"


CAN_INTERFACE = 'can0'
OUTPUT_FILENAME = "raw_can_receiver.log"
PRINT_TO_CONSOLE = False

CAN_FRAME_FORMAT = '=IB3x8s'
CAN_FRAME_SIZE = struct.calcsize(CAN_FRAME_FORMAT)
FILEMODE_WRITE = 'w'


def main():
    can_socket = socket.socket(socket.AF_CAN, socket.SOCK_RAW, socket.CAN_RAW)
    can_socket.bind((CAN_INTERFACE,))

    with open(OUTPUT_FILENAME, FILEMODE_WRITE) as outputfile:
        while True:
            can_frame, _ = can_socket.recvfrom(CAN_FRAME_SIZE)
            can_id, can_dlc, can_data = struct.unpack(CAN_FRAME_FORMAT, can_frame)

            datastring = " ".join("{:02X}".format(x) for x in can_data[:can_dlc])
            output_text = "({0:14.3f})   CAN Id: {1:4.0f} (Hex {1:3X})    Data: {2} \n".format(
                    time.time(), can_id, datastring)

            outputfile.write(output_text)
            outputfile.flush()

            if PRINT_TO_CONSOLE:
                print(output_text)

if __name__ == '__main__':
    main()

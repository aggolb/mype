''' 
## MYPE LOCAL 1.0
## 
## WHAT:
## (my)Sky(pe) A shot at (semi-reliable) UDP video chat over LAN
##
## HOW:
## Open mype.py and enter the IP Address of the person you're calling.
## Click "Connect" and wait for them to accept your call.
##
## NOTES:
## While it works, this wasn't meant to be a fully fledged chat app. It was made strictly for educational purposes
## It uses Tkinter for the GUI which while easy to use isn't very "thread safe" and lacks a good amount
##   of features that are available from other industry players. As such there are a few GUI related hacks sprinkled in
##   to get the desired results.
## OpenCV is used strictly for the purpose of camera access, so can esily be swapped put with a smaller library
##   without too much trouble
##
## Author: Shimpano Mutangama
'''

from pyaudio import PyAudio,paInt16
import Tkinter as tk
from PIL import Image, ImageTk
import cv2
import time
import threading
import socket
from io import BytesIO
import sys

class VideoWindow:

    def __init__(self):
        self.main_window = tk.Tk()
        
        #The window for the frame taken by the webcam
        self.captured_frame_box = None
        self.captured_video_frame = None
        
        #The window for the frame received from the network
        self.received_frame_box = None
        self.received_video_frame = None

        self.dialog = tkMessageBox
        #Link the clients
        self.video_client = None
        self.audio_client = None
        
        #Link the servers
        self.video_server = None
        self.audio_server = None

        #Link the camera
        self.camera = None

        #Link the coordinator
        self.coordinator = None

        #These will be used to connect and disconnect
        self.input_box = None
        self.button_text = None
        self.connect_button = None

        #Check if user in call
        self.in_call = False
        
        self._prepare_main_window()

    def start_window(self):
        
        t = threading.Thread(target = self.run,name="Window Thread")
        t.daemon = True
        t.start()
        
    def run(self):
        self.main_window.mainloop()
        
    def _prepare_main_window(self):
        
        self.main_window.title("Video Chat App")
        self.main_window.wm_protocol("WM_DELETE_WINDOW",self.on_close)
        #Fixed size
        self.main_window.resizable(width = False, height = False)

        #Contains connection options
        options_frame = tk.Frame(self.main_window, width = 320)
        options_frame.pack()
        
        #Used to input IP Address
        self.input_box = tk.Entry(options_frame, width = 40)
        self.input_box.pack(side = tk.LEFT)
        
        #Connect Button
        self.button_text = tk.StringVar()
        self.button_text.set("Connect")
        self.connect_button = tk.Button(options_frame, text = "Connect")
        self.connect_button.pack(side = tk.LEFT)
        self.connect_button.bind('<Button-1>',self.start_connection)

        #Contains the received video frame
        self.received_frame_box = tk.Frame(self.main_window, width = 320, height = 240, bg = "#000000")
        self.received_frame_box.pack(fill=tk.X)
        
        #Contains the image
        self.received_video_frame = tk.Label(self.received_frame_box,bg="#000000")
        self.received_video_frame.pack(fill=tk.X)

        #Contains the captured video frame
        self.captured_frame_box = tk.Frame(self.main_window, width = 320, height = 240, bg = "#000000")
        self.captured_frame_box.pack(fill=tk.X)
        
        #Contains the image
        self.captured_video_frame = tk.Label(self.captured_frame_box,bg="#000000")
        self.captured_video_frame.pack(fill=tk.X)

        #Call Options
        self.call_options_frame = tk.Frame(self.main_window,height = 200)
        self.call_options_frame.pack_forget()

        #Answer Button
        self.answer_button = tk.Button(self.call_options_frame, text = "Answer", command = self.answer_call)
        self.answer_button.pack(side = tk.LEFT)
        self.reject_button = tk.Button(self.call_options_frame, text = "Reject", command = self.reject_call)
        self.reject_button.pack(side = tk.LEFT)

    def answer_call(self):
        
        client_address = self.coordinator.temp_client
        ip_address = client_address[0]

        #Tell the caller you accept
        self.coordinator.c_server_socket.sendto("accepted",client_address)

        #Set the address of the callers coordinator
        self.coordinator.connected_address = (ip_address,1002)
        self.coordinator.available = False
        self.connect_button.configure(text="Disconnect")
        self.in_call = True
        
        #Connect to the caller
        self.video_client.start_client(client_address[0])
        self.audio_client.start_client(client_address[0])
        self.coordinator.temp_client = None

        #Hide the call options
        self.call_options_frame.pack_forget()

    def reject_call(self):
        client_address = self.coordinator.temp_client
        #Tell the caller you decline
        self.coordinator.c_server_socket.sendto("rejected",client_address)
        #Hide the call options
        self.call_options_frame.pack_forget()

    def connect(self):
        
        if self.in_call == False:
            
            self.connect_button.configure(text="Calling")
            
            #Get Ip Address from input box
            ip_address = self.input_box.get()
            result = self.coordinator.make_call(ip_address)
            
            if result == True:
                
                #Disable calls
                self.connect_button.configure(text="Disconnect")
                self.in_call = True
                self.coordinator.available = False
                self.video_client.start_client(ip_address)
                self.audio_client.start_client(ip_address)
                
            else:
                
                self.connect_button.configure(text="Connect")
                self.in_call = False
                print "Call Failed"
            
        else:
            self.connect_button.configure(text="Connect")
            self.in_call = False
            #Enable Calls
            self.coordinator.end_call()
            self.video_server.running = False
            self.video_client.running = False
            self.audio_server.running = False
            self.audio_client.running = False

           
    
    def start_connection(self,event):
        #The GUI runs in a single thread loop, doing something like making a call would
        #would block and all UI elements including the camera output would freeze
        #using a daemon thread helps avoid this effect
        t = threading.Thread(target = self.connect)
        t.daemon = True
        t.start()
         
   

    def show_received_frame(self,frame):
        
        frame = Image.open(frame)
        #Place Image
        image = ImageTk.PhotoImage(frame)
        self.received_video_frame.image = image
        self.received_video_frame.configure(image = image)
        
        #time.sleep(0.03)
    
    def show_captured_frame(self,frame):
        
        #Flip the pixel color data
        frame = cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
        
        #Convert frame array to image
        frame = Image.fromarray(frame)
        frame = frame.resize((160,120),Image.ANTIALIAS)

        #Place Image
        image = ImageTk.PhotoImage(frame)
        self.captured_video_frame.image = image
        self.captured_video_frame.configure(image = image)
        
        #time.sleep(0.03)


    def on_close(self):
        
        self.camera.running = False
        self.video_server.listening = False
        self.video_server.running = False
        self.audio_server.listening = False
        self.audio_server.running = False
        self.video_client.running = False
        self.audio_client.running = False

        print "\nClosing..."
        
        self.main_window.destroy()
        self.main_window.quit()
        
#The Coordinator Class Coordinates Calls, it listens for calls, makes calls and ends calls.
#It doesn't handle the actual transmission over voice or video
class Coordinator:

    def __init__(self):
        
        self.video_server = None
        self.video_client = None
        self.audio_server = None
        self.audio_client = None
        self.c_server_socket = None
        self.c_client_socket = None
        self.available = True
        self.window = None
        
        #The address of the client with an accepted call
        self.connected_address = None
        #Temporarily stores the client whose making a request
        self.temp_client = None


    def make_call(self,ip_address):
        
        HOST = ip_address
        PORT = 1002
        calling_address = (HOST,PORT)
        
        try:
            self.c_client_socket.sendto("call",calling_address)
            data, addr = self.c_client_socket.recvfrom(1024)
            
            print data
            
            if data == "accepted":
                self.available = False
                self.connected_address = calling_address
                return True
            elif data == "rejected":
                return False
            
        except:
            return False

    def end_call(self):

        self.c_client_socket.sendto("endcall",self.connected_address)
        self.available = True
        #The host,port pair for the user currently in a call with
        self.connected_address = None
    
    def start_server(self):
        t = threading.Thread(target = self.run)
        t.daemon = True
        t.start()

    def run(self):
        HOST = '0.0.0.0'
        PORT = 1002

        self.c_server_socket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.c_server_socket.bind((HOST,PORT))
        self.c_client_socket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        #Determine how long you can try to connect, basically maximum ring time before giving up
        #ring time 20 seconds
        self.c_client_socket.settimeout(20)

        while True:
            #Wait for requests
            data,client_address = self.c_server_socket.recvfrom(1024)
            ip_address = client_address[0]
            
            #Handle request
            if data == "call":
                
                print "Availability: ",self.available
                
                if self.available == True:
                    self.temp_client = client_address
                    self.window.call_options_frame.pack()
                    #The GUI will now handle accepting or rejecting the call
                else:
                    self.c_server_socket.sendto("rejected",client_address)
                  

            elif data == "endcall":
                print "Ending call.."
                self.window.connect_button.configure(text="Connect")
                self.window.in_call = False
                self.available = True
                self.connected_address = None
                self.video_client.running = False
                self.video_server.running = False
                self.audio_client.running = False
                self.audio_server.running = False
                                           
                
class Camera:
    
    def __init__(self):
        
        self.webcam = None
        self.running = True
        self.current_frame = None

    def start_camera(self):
        
        t = threading.Thread(target = self.poll_camera)
        t.daemon = True
        t.start()
        
    def poll_camera(self):
        
        self.webcam = cv2.VideoCapture(0)
        while self.running:
            success, self.current_frame = self.webcam.read()
        self.webcam.release()
        print "\ncamera shut down"

class VideoServer:

    def __init__(self):
            
        self.video_socket = None
        self.video_client = None
        self.camera = None
        self.client_address = None
        
        #Check if a call is happening
        self.running = False
        #Check if server is listening for connections
        self.listening = True
        
        #Determines whether the server can accept calls
        self.accept_calls = True

    def start_server(self):
        
        t = threading.Thread(target = self.run, name = "Video Server Thread")
        t.daemon = True
        t.start()

    def run(self):

        HOST = '0.0.0.0'
        PORT = 1000
        
        self.video_socket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.video_socket.bind((HOST,PORT))

        

        while self.listening:
            
            #Wait for someone to connect to you
            data,self.client_address = self.video_socket.recvfrom(1024)
            if data != "start":
                continue
            print "\nConnection to video feed from: ",self.client_address
            self.running = True
            self.broadcast_video()
        print "\nvideo server shut down"

    def broadcast_video(self):

        while self.running:
            
            #Just in case the camera hasn't started getting frames yet
            if self.camera.current_frame is not None:
                frame = cv2.cvtColor(self.camera.current_frame,cv2.COLOR_BGR2RGB)
                image = Image.fromarray(frame)
                image = image.resize((320,240),Image.ANTIALIAS)

                #Save the image as a JPEG in memory
                image_bytes = BytesIO()
                image.save(image_bytes,format = "JPEG",quality = 50)
                image_bytes.seek(0)
                #print "Memory jpeg is %s bytes"%len(image_bytes.getvalue())
                try:
                    
                    self.video_socket.settimeout(1)
                    data = image_bytes.read(60000)
                    #print "Starting to read"
                    while data:
                        
                        self.video_socket.sendto(data,self.client_address)
                        ack = self.video_socket.recvfrom(1024)
                        data = image_bytes.read(60000)
                        
                    self.video_socket.sendto("end",self.client_address)
                    ack = self.video_socket.recvfrom(1024)
                    #print "finished reading"
                    self.video_socket.settimeout(None)
                    
                except:
                    #If there is a timeout error, keep trying
                    self.video_socket.settimeout(None)
                    pass


class AudioServer:

    def __init__(self):
        
        self.audio_socket = None
        self.accept_calls = True
        self.client_address = None
        self.audio_client = None
        self.audio_recorder = None
        self.listening = True
        self.running = False

    def start_server(self):
        
        t = threading.Thread(target = self.run, name="Audio Server Thread")
        t.daemon = True
        t.start()

    def run(self):

        HOST = '0.0.0.0'
        PORT = 1001

        self.audio_socket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.audio_socket.bind((HOST,PORT))

        
        #Ideally want the server to run for the duration of the program listening for connections
        while self.listening:

            #Wait for someone to connect
            data,self.client_address = self.audio_socket.recvfrom(1024)
            if data != "start":
                continue
            print "\nConnection to audio feed from: ",self.client_address
            self.running = True
            self.broadcast_audio()
        print "\naudio server shut down"

    def broadcast_audio(self):
        
        CHUNK = 1024
        FORMAT = paInt16
        CHANNELS = 2
        RATE = 44100

        p = PyAudio()
        self.audio_recorder = p.open(format = FORMAT,
                                     channels = CHANNELS,
                                     rate = RATE,
                                     input = True,
                                     frames_per_buffer = CHUNK)

        while self.running:
            try:
                data = self.audio_recorder.read(1024)
            except:
                continue

            #Given our pyaudio params, each read will be 4096 bytes
            data = bytes(data)
            self.audio_socket.sendto(data,self.client_address)
            try:
                self.audio_socket.settimeout(3)
                ack = self.audio_socket.recvform(1024)
                self.audio_socket.settimeout(None)
            except:
                self.audio_socket.settimeout(None)
                pass

        self.audio_recorder.close()
        print "Done with call"
        

class VideoClient:

    def __init__(self):
        
        self.video_socket = None
        self.server_address = None

        #The client will update the window when an image arrives
        self.window = None
        
        #Checks if thread allowed to run
        self.running = False

    def start_client(self,ip_address):
        
        t = threading.Thread(target = self.run,args = (ip_address,),name = "Video Client Thread")
        t.daemon = True
        t.start()

    def run(self,ip_address):
        self.running = True
        HOST = ip_address
        PORT = 1000 #standard for video

        self.video_socket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.server_address = (HOST,PORT)
        self.video_socket.sendto("start",self.server_address)

        self.display_video()

    def display_video(self):
        
        print "\nReceiving Video..."
        
        while self.running:
            try:
                self.video_socket.settimeout(1)
                image_bytes = BytesIO()
                data,addr = self.video_socket.recvfrom(60000)
                
                while True:
                    if data[-3:] == "end":
                        image_bytes.write(data[:-3])
                        self.video_socket.sendto("ack",self.server_address)
                        break
                    image_bytes.write(data)
                    self.video_socket.sendto("ack",self.server_address)
                    data,addr = self.video_socket.recvfrom(60000)

                
                image_bytes.seek(0)
                #t = threading.Thread(target = self.window.show_received_frame,args=(image_bytes,))
                #t.daemon = True
                #t.start()
                self.window.show_received_frame(image_bytes)
                self.video_socket.settimeout(None)
            except:
                #Even if there's a timeout keep trying to receive video
                self.video_socket.settimeout(None)
                pass
        print "\nvideo client shut down"

class AudioClient:

    def __init__(self):
        
        self.audio_socket = None
        self.server_address = None
        self.audio_player =  None
        self.running = False
        

    def start_client(self,ip_address):
        t = threading.Thread(target = self.run,args = (ip_address,),name = "Audio Client Thread")
        t.daemon = True
        t.start()

    def run(self,ip_address):
        
        self.running = True
        
        HOST = ip_address
        PORT = 1001
        
        self.server_address = (HOST,1001)
        self.audio_socket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.audio_socket.sendto("start",self.server_address)

        CHUNK = 1024
        RATE = 44100
        CHANNELS = 2
        FORMAT = paInt16

        p = PyAudio()
        self.audio_player = p.open(format = FORMAT,
                                   rate = RATE,
                                   channels = CHANNELS,
                                   output = True)
        while self.running:

            try:
                self.audio_socket.settimeout(3)
                data, server = self.audio_socket.recvfrom(4096)
                #play audio
                self.audio_player.write(data)
                self.audio_socket.sendto("ack",self.server_address)
                self.audio_socket.settimeout(None)
            except:
                self.audio_socket.settimeout(None)
                pass
            

            
            
        print "\naudio client shut down"

                
            

class App:

    def __init__(self):
        
        self.webcam = Camera()
        self.window = VideoWindow()

        #Initialize coordinator
        self.coordinator = Coordinator()
        
        #Initialize servers
        self.video_server = VideoServer()
        self.audio_server = AudioServer()

        #Initialize clients
        self.video_client = VideoClient()
        self.audio_client = AudioClient()

        #Video server needs to ask camera for most recent image
        self.video_server.camera = self.webcam

        #Client needs to be able to change gui
        self.video_client.window = self.window

        #Coordinator needs to contril clients and servers
        self.coordinator.video_client = self.video_client
        self.coordinator.video_server = self.video_server
        self.coordinator.audio_client = self.audio_client
        self.coordinator.audio_server = self.audio_server
        self.coordinator.window = self.window
        
        #Window needs to control client and servers
        self.window.video_client = self.video_client
        self.window.audio_client = self.audio_client
        self.window.video_server = self.video_server
        self.window.audio_server = self.audio_server
        self.window.coordinator = self.coordinator
        self.window.camera = self.webcam

        #The servers need to block incoming calls if already in a call
        self.video_server.video_client = self.video_client
        self.audio_server.audio_client = self.audio_client

    def start(self):
        
        self.coordinator.start_server()
        self.webcam.start_camera()
        #Start and wait for connections
        self.video_server.start_server()
        self.audio_server.start_server()
        self.window.start_window()

        while self.webcam.running:
            
            #Show user their own mirror image
            current_frame = self.webcam.current_frame
            frame = cv2.flip(current_frame,1)

            if frame is not None:

                try:
                    self.window.show_captured_frame(frame)
                    time.sleep(0.01)
                except:
                    pass

        print "\napp shut down..."
        

        

def main():
    app = App()
    app.start()
    
    
    
    
if __name__=="__main__":
    main()


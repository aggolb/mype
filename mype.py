'''
## mype local 1.0
## 
## WHAT:
## (my)Sky(pe) my shot at video chat over LAN
##
## HOW:
## Open mype.py and enter the IP Address of the person you're calling.
## Click "Connect" and wait
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
        
        #Link the clients
        self.video_client = None
        self.audio_client = None
        
        #Link the servers
        self.video_server = None
        self.audio_server = None

        #Link the camera
        self.camera = None

        #These will be used to connect and disconnect
        self.input_box = None
        self.button_text = None
        
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
        connect_button = tk.Button(options_frame, textvariable = self.button_text)
        connect_button.pack(side = tk.LEFT)
        connect_button.bind('<Button-1>',self.connect)

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

    def connect(self,event):
        
        text = self.button_text.get()
        if text == "Connect":

            #Get Ip Address from input box
            ip_address = self.input_box.get()
            
            #Disable calls
            self.video_server.accept_calls = False
            self.video_client.start_client(ip_address)
            self.audio_server.accept_calls = False
            self.audio_client.start_client(ip_address)
            
        else:
            self.button_text.set("Connect")

            #Enable Calls
            self.video_server.accept_calls = True
            self.video_server.running = False
            self.video_client.running = False
            self.audio_server.accept_calls = True
            self.audio_server.running = False
            self.audio_client.running = False
            
   

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
            print "\nWaiting for a connection to video feed..."
            data,self.client_address = self.video_socket.recvfrom(1024)
            print "\nConnection to video feed from: ",self.client_address

            #If a user I'm not yet connected to asks for my video feed,start a
            #client to ask for theirs
            if self.accept_calls == True:
                self.video_client.start_client(self.client_address[0])

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
                    
                    self.video_socket.settimeout(3)
                    data = image_bytes.read(4096)
                    #print "Starting to read"
                    while data:
                        
                        self.video_socket.sendto(data,self.client_address)
                        ack = self.video_socket.recvfrom(1024)
                        data = image_bytes.read(4096)
                        
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
            print "\nWaiting for a connection to audio feed..."
            data,self.client_address = self.audio_socket.recvfrom(1024)
            print "\nConnection to audio feed from: ",self.client_address
            #If not yet connected, conncect
            if self.accept_calls:
                self.audio_client.start_client(self.client_address[0])

            self.running = True
            self.broadcast_audio()
        print "\naudio server shut down"

    def broadcast_audio(self):
        while self.running:
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
        self.update_window_button()
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
                self.video_socket.settimeout(3)
                image_bytes = BytesIO()
                data,addr = self.video_socket.recvfrom(4096)
                
                while True:
                    if data[-3:] == "end":
                        image_bytes.write(data[:-3])
                        self.video_socket.sendto("ack",self.server_address)
                        break
                    image_bytes.write(data)
                    self.video_socket.sendto("ack",self.server_address)
                    data,addr = self.video_socket.recvfrom(4096)

                
                image_bytes.seek(0)
                self.window.show_received_frame(image_bytes)
                self.video_socket.settimeout(None)
            except:
                #Even if there's a timeout keep trying to receive video
                self.video_socket.settimeout(None)
                pass
        print "\nvideo client shut down"

    def update_window_button(self):
        #We want the GUI to know when the client has been trigged, i.e.
        #is in the process of reciving a feed, so we know to show "Connect or Disconnect Button
        self.window.button_text.set("Disconnect")
                
    

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
                self.audio_socket.settimeout(None)
            except:
                self.audio_socket.settimeout(None)
                pass

            self.audio_socket.sendto("ack",self.server_address)
            
        print "\naudio client shut down"

                
            

class App:

    def __init__(self):
        
        self.webcam = Camera()
        self.window = VideoWindow()
        
        #Initialize servers
        self.video_server = VideoServer()
        self.audio_server = AudioServer()

        #Initialize clientd
        self.video_client = VideoClient()
        self.audio_client = AudioClient()

        #Video server needs to ask camera for most recent image
        self.video_server.camera = self.webcam

        #Client needs to be able to change gui
        self.video_client.window = self.window
        
        #Window needs to control client and servers
        self.window.video_client = self.video_client
        self.window.audio_client = self.audio_client
        self.window.video_server = self.video_server
        self.window.audio_server = self.audio_server
        self.window.camera = self.webcam

        #The servers need to block incoming calls if already in a call
        self.video_server.video_client = self.video_client
        self.audio_server.audio_client = self.audio_client

    def start(self):

        self.webcam.start_camera()
        self.window.start_window()

        #Start and wait for connections
        self.video_server.start_server()
        self.audio_server.start_server()

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


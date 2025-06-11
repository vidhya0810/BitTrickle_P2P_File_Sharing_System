from socket import *
import sys
import threading
import time
import os


server_name="127.0.0.1"
server_port=int(sys.argv[1])

trigger_stop=threading.Event()   ## To stop all threads gracefully


# ***************FUNCTION TO AUTHENTICATE CLIENT****************#

def authentication(clientSocket,peer_port):

    autheticated= False

    while not autheticated:       
        username=input("Enter username:")
        password=input("Enter password:")

        message= f"AUTH {username} {password}"

        clientSocket.sendto(message.encode(), (server_name, server_port))

        response,serverAddress = clientSocket.recvfrom(1024)

        response= response.decode()

        if response == "Yes":
            autheticated=True
            string1="Welcome to BitTrickle!"
            string2="Available commands are: 1) get 2)lap 3)lpf 4)pub 5)sch 6)unp 7)xit"
            message=string1+ '\n' +string2
            print(message)

            TCP_port_register=f"TCP {username} {peer_port}"
            clientSocket.sendto(TCP_port_register.encode(), (server_name, server_port))

            return True
        
        else:
            autheticated=False
            message="Authentication failed.Please try again."
            print(message)

#****************FUNCTION TO SEND HEARTBEAT TO THE SERVER***********************#
    
def sendHBT(clientSocket):
    while not trigger_stop.is_set():
        message="HBT"
        try:
            clientSocket.sendto(message.encode(),(server_name, server_port))
        except OSError:
            break
        time.sleep(2)
    
#*****************FUNCTION TO HANDLE REQUEST/COMMANDS FROM THE USER************#    
        
def handleRequest(clientSocket:socket):
    while not trigger_stop.is_set():
        command=input("Enter a number from 1 - 7: ")

#***************************GET FILE***************************#

        if command=="1":  ##GET
            filename=input("Enter the filename to Download: ")
            message=f"CMD {command} {filename}" 
            clientSocket.sendto(message.encode(),(server_name, server_port))
            response,serverAddress = clientSocket.recvfrom(1024)
            response= response.decode()

            if response=="Download Failed":
                print("File Not Found.")
            else:
                download_port=int(response)
                if p2pFileDownload(filename, download_port):
                    print(f"{filename} downloaded successfully.")
                else:
                    print("File Not Found.")
                

#*********************LIST ACTIVE PEERS***********************#

        if command == "2":  ##LAP
            message=f"CMD {command}" 
            clientSocket.sendto(message.encode(),(server_name, server_port))
            response,serverAddress = clientSocket.recvfrom(1024)
            response= response.decode()
            if response=="0":
                print("No active peers.")
            else:
                active_peers_list=response.split()
                active_peers_list_len=len(active_peers_list)
                if active_peers_list_len==1:
                    print("1 Active Peer:")
                    print(response)
                else:
                    print(f"{active_peers_list_len} active peers:")
                    for i in range(active_peers_list_len):
                        print(active_peers_list[i])

#********************LIST PUBLISHED FILES**********************#

        if command=="3":  ##LPF
            message=f"CMD {command}"
            clientSocket.sendto(message.encode(),(server_name, server_port))
            response,serverAddress = clientSocket.recvfrom(1024)
            response= response.decode()

            if response=="Empty":
                print("No files published")
            
            else:
                files_list=response.split(',')
                if len(files_list)==1:
                    print(f"1 file published:\n{files_list[0]}")
                else:
                    print(f"{len(files_list)} files published:")
                    for file in files_list:
                        print(file)    
              
#**************************PUBLISH A FILE********************#

        if command== "4":  ##PUB
            filename=input("Enter the filename to publish: ")
            message=f"CMD {command} {filename}" 
            clientSocket.sendto(message.encode(),(server_name, server_port))
            response,serverAddress = clientSocket.recvfrom(1024)
            response= response.decode()
            print(response)


#*****************SEARCH FOR SUBSTRING IN THE PUBLISHED FILES***************#
        
        if command=="5":  ##SCH
            substr_to_search=input("Enter the substring to search: ")
            message=f"CMD {command} {substr_to_search}" 
            clientSocket.sendto(message.encode(),(server_name, server_port))
            response,serverAddress = clientSocket.recvfrom(1024)
            response= response.decode()

            if response=="No files found.":
                print(response)
            else:
                matched_files=response.split(',')
                if len(matched_files)==1:
                    print(f"1 file found:\n{matched_files[0]}")
                
                else:
                    print(f"{len(matched_files)} files found:")
                    for file in matched_files:
                        print(file)

#**********************************UNPUBLISH A FILE****************#

        
        if command=="6": ##UNP
            filename=input("Enter the filename to unpublish: ")
            message=f"CMD {command} {filename}" 
            clientSocket.sendto(message.encode(),(server_name, server_port))
            response,serverAddress = clientSocket.recvfrom(1024)
            response= response.decode()
            print(response)

#****************************EXIT FROM THE CODE*******************#

        if command == "7":  ##XIT
          
            print("Goodbye!")
            trigger_stop.set()
            clientSocket.close()
            break

#*****THREAD LISTENING TO TCP WELCOME SOCKET AND SEND REQUESTED FILE TO THE CLIENT********#

def p2pFileServer(welcoming_socket:socket):
    
    welcoming_socket.settimeout(1)
    while not trigger_stop.is_set():
        try:
            connection_socket,_ =welcoming_socket.accept()
            connection_socket.settimeout(1)
            with connection_socket:
                requested_file=connection_socket.recv(1024).decode()

                if os.path.exists(requested_file):
                    with open(requested_file, 'rb') as file:
                        data=file.read(1024)
                        while data:
                            try:
                                connection_socket.send(data)
                            except OSError:
                                break

                            data=file.read(1024)
                
            
                else:
                    connection_socket.send(b"Error: File Not found")
        except timeout:
            continue
        except OSError:
            break

#********************FUNCTION TO DOWNLOAD THE REQUESTED FILE****************#


def p2pFileDownload(filename, peer_port):
    download_socket=socket(AF_INET,SOCK_STREAM)
    try:

        download_socket.connect(("localhost",peer_port))
        download_socket.send(filename.encode())

        with open (filename,'wb') as file:
            while True:
                data=download_socket.recv(1024)
                if not data:
                    break
                if data==b"Error: File Not found":
                    return False
                file.write(data)
    except(ConnectionError,OSError):
        print("Error during download.")
        return False
    finally:
        download_socket.close()
    return True


def main():
    
    ##UDP SOCKET FOR SERVER COMMUNICATION
    clientSocket= socket(AF_INET, SOCK_DGRAM)

    ##TCP SOCKET FOR P2P COMMUNICATION
    p2p_welcoming_socket=socket(AF_INET,SOCK_STREAM)
    p2p_welcoming_socket.bind(("localhost",0))
    p2p_welcoming_socket.listen()

    peer_port=p2p_welcoming_socket.getsockname()[1]

    if authentication(clientSocket,peer_port):

        ##THREAD FOR SENDING HEARTBEAT TO THE SERVER
        send_heartbeat_thread=threading.Thread(target=sendHBT,args=(clientSocket,))

        ##THREAD FOR HANDLING USER REQUEST/COMMANDS
        process_request_thread=threading.Thread(target=handleRequest,args=(clientSocket,))

        ##THREAD LISTENING TO WELCOME SOCKET
        tcp_file_server_thread=threading.Thread(target=p2pFileServer,args=(p2p_welcoming_socket,))


        send_heartbeat_thread.start()
        process_request_thread.start()
        tcp_file_server_thread.start()

        process_request_thread.join()

        trigger_stop.set()
        
        send_heartbeat_thread.join()
        tcp_file_server_thread.join()

        clientSocket.close()
        p2p_welcoming_socket.close()


if __name__ == '__main__':
    main()



from socket import *
import sys
import datetime
import time
import threading

class Server:
    def __init__(self,host,port,credential_file):
        self.credentials_dict={}
        self.authenticated_clients={}
        self.active_client_heartbeat ={}
        self.active_users=[]
        self.HBT_TIMEOUT=3
        self.published_files={}
        self.clientTCPsockets={}
        self.serverHost=host
        self.serverPort=port
        self.serverAddress=(self.serverHost,self.serverPort)
        self.serverSocket=socket(AF_INET, SOCK_DGRAM)
        self.serverSocket.bind(self.serverAddress)  

        self.load_credentials(credential_file) 

        ##Thread to check for inactive clients 

        threading.Thread(target=self.remove_inactive_peers,daemon=True).start()

    ## Load credential file and store in dictionary

    def load_credentials(self,filename):
        with open(filename, 'r') as file:
            for line in file:
                username,password=line.strip().split()
                self.credentials_dict[username]=password 
    
    ##Check for client authentication
    
    def client_authorised(self,uname,pwd):
        return uname in self.credentials_dict and self.credentials_dict[uname]==pwd
    
    ## Function to list active peers
    
    def list_active_peers(self,clientPort_issuing_query,clientAddress):
        self.active_users=[value for key,value in self.authenticated_clients.items() if key !=clientPort_issuing_query]
        if not self.active_users:
            message="0"
        else:
            message=' '.join(self.active_users)
        print(f"{datetime.datetime.now()} :{clientPort_issuing_query}:Sent OK to {self.authenticated_clients[clientPort_issuing_query]}")
        self.serverSocket.sendto(message.encode('utf-8'),clientAddress)

    ## Function that continuously checks for inactive peers
    
    def remove_inactive_peers(self):
        while True:
            current_time=time.time()
            inactive_peers=[]

            for client in self.active_client_heartbeat.keys():
                if current_time - self.active_client_heartbeat[client]> self.HBT_TIMEOUT:
                    inactive_peers.append(client)
            
            for client in inactive_peers:
                del self.authenticated_clients[client]
                del self.active_client_heartbeat[client]
            
            time.sleep(1)
    
    ## Handle Publish file request from the user

    def insert_files(self,username,filename,clientPort,clientAddress):

            if username in self.published_files.keys():
                if filename in self.published_files[username]:
                    message="File published successfully"
                else:
                    self.published_files[username].append(filename)
            
            else:
                self.published_files[username]=[filename]

            message="File published successfully"
            print(f"{datetime.datetime.now()} :{clientPort}:Sent OK to {self.authenticated_clients[clientPort]}")
            self.serverSocket.sendto(message.encode('utf-8'),clientAddress)

    ## Handle List published files request from the user 

    def list_published_files(self,username,clientPort,clientAddress):

           
        if username in self.published_files.keys():
            if len(self.published_files[username])!=0:
                message=','.join(self.published_files[username])
            else:
                message="Empty"

        else:
            message="Empty"

        print(f"{datetime.datetime.now()} :{clientPort}:Sent OK to {self.authenticated_clients[clientPort]}")
        self.serverSocket.sendto(message.encode('utf-8'),clientAddress)
    
    ## Handle Unpublish file request from the user

    def unpublish_file(self,username,filename,clientPort,clientAddress):
        if username in self.published_files.keys():
            if filename in self.published_files[username]:
                self.published_files[username].remove(filename)
                message="File unpublished successfully"
                print(f"{datetime.datetime.now()} :{clientPort}:Sent OK to {self.authenticated_clients[clientPort]}")
            else:
                message="File Unpublication failed. No such file published earlier."
                print(f"{datetime.datetime.now()} :{clientPort}:Sent ERR to {self.authenticated_clients[clientPort]}")
        else:
            message="File unpublication failed. User not published any file."
            print(f"{datetime.datetime.now()} :{clientPort}:Sent ERR to {self.authenticated_clients[clientPort]}")
               
        
        self.serverSocket.sendto(message.encode('utf-8'),clientAddress)

    ## Handle search request from the user
    
    def search_file_with_substr(self,username,search_string,clientPort,clientAddress):
        result_files=[]
        active_peers=[value for key,value in self.authenticated_clients.items() if key !=clientPort]

        for peer, files in self.published_files.items():

            if peer!=username and peer in active_peers:

                matched_files=[file for file in files if search_string in file]
                result_files.extend(matched_files)
        
        if result_files:
            message=','.join(result_files)
        else:
            message="No files found."  

        print(f"Result files :{result_files}")
        
        print(f"{datetime.datetime.now()} :{clientPort}:Sent OK to {self.authenticated_clients[clientPort]}")
        self.serverSocket.sendto(message.encode('utf-8'),clientAddress)
    

    ## Helper function to find the peer with requested file and return TCP port 
    
    def find_peer_with_file(self,filename,clientPort,clientAddress):
        TCP_port=0
        active_peers=[value for key,value in self.authenticated_clients.items() if key !=clientPort]
        for username,files in self.published_files.items():
            if username in active_peers and filename in files:
                TCP_port=self.clientTCPsockets[username]

        if TCP_port!=0:
            message=TCP_port
            print(f"{datetime.datetime.now()} :{clientPort}:Sent OK to {self.authenticated_clients[clientPort]}")
        else:
            message="Download Failed"
            print(f"{datetime.datetime.now()} :{clientPort}:Sent ERR to {self.authenticated_clients[clientPort]}")
        
        self.serverSocket.sendto(message.encode('utf-8'),clientAddress)
        
    ## Main Thread to handle all the requests from user

    def run(self):
        while True:
            message,clientAddress= self.serverSocket.recvfrom(1024)
            clientPort=clientAddress[1]
            decoded_message=message.decode()

            if decoded_message.startswith("TCP"):
                 _,username,TCP_port=decoded_message.split()
                 self.clientTCPsockets[username]=TCP_port 
                
                
            if decoded_message.startswith("AUTH"):
                _,username,password=decoded_message.split()
                print(f"{datetime.datetime.now()} :{clientPort}: Received AUTH from {username}")
                
                if self.client_authorised(username,password) and username not in self.authenticated_clients.values():
                    self.authenticated_clients[clientPort]=username
                    self.active_client_heartbeat[clientPort]=time.time()
                    message="Yes"
                    print(f"{datetime.datetime.now()} :{clientPort}:Sent OK to {username}")
                    self.serverSocket.sendto(message.encode('utf-8'),clientAddress)
                
                else:
                    message= "No"
                    print(f"{datetime.datetime.now()} :{clientPort}:Sent ERR to {username}")
                    self.serverSocket.sendto(message.encode('utf-8'),clientAddress)
            
            elif decoded_message.startswith("HBT"):
                if clientPort in self.authenticated_clients:
                    print(f"{datetime.datetime.now()} :{clientPort}: Received HBT from {self.authenticated_clients[clientPort]}")
                    self.active_client_heartbeat[clientPort]=time.time()
            
            elif decoded_message.startswith("CMD"):
                if clientPort in self.authenticated_clients:
                    command=decoded_message[4]

                    if command=='1':   ## GET command
                        print(f"{datetime.datetime.now()} :{clientPort}: Received GET from {self.authenticated_clients[clientPort]}")
                        filename=decoded_message[6:]
                        self.find_peer_with_file(filename,clientPort,clientAddress)

                    
                    elif command=='2': ## LAP command
                        print(f"{datetime.datetime.now()} :{clientPort}: Received LAP from {self.authenticated_clients[clientPort]}")
                        self.list_active_peers(clientPort,clientAddress)
                    
                    elif command=='3': ##LPF command
                        print(f"{datetime.datetime.now()} :{clientPort}: Received LPF from {self.authenticated_clients[clientPort]}")
                        self.list_published_files(self.authenticated_clients[clientPort],clientPort,clientAddress)

                    elif command=='4': ## PUB command
                        print(f"{datetime.datetime.now()} :{clientPort}: Received PUB from {self.authenticated_clients[clientPort]}")
                        filename=decoded_message[6:]
                        self.insert_files(self.authenticated_clients[clientPort],filename,clientPort,clientAddress)
                    
                    elif command=='5': ##SCH command
                        print(f"{datetime.datetime.now()} :{clientPort}: Received SCH from {self.authenticated_clients[clientPort]}")
                        substr_to_search=decoded_message[6:] 
                        print(f"Substr to search {substr_to_search}")
                        self.search_file_with_substr(self.authenticated_clients[clientPort],substr_to_search,clientPort,clientAddress)

                    elif command=='6': ##UNP command
                        print(f"{datetime.datetime.now()} :{clientPort}: Received UNP from {self.authenticated_clients[clientPort]}")
                        filename=decoded_message[6:]
                        self.unpublish_file(self.authenticated_clients[clientPort],filename,clientPort,clientAddress)

                    elif command=='7':  ##XIT command
                        print(f"{datetime.datetime.now()} :{clientPort}: Received XIT from {self.authenticated_clients[clientPort]}")

            
if __name__== '__main__':
    if len(sys.argv)<2:
        print("Please provide the port number")
        sys.exit(1)
    print(f"Server started and listening on port {int(sys.argv[1])} ")
    server=Server("127.0.0.1",int(sys.argv[1]),'credentials.txt')
    server.run()



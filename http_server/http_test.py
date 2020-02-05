from  http.server import BaseHTTPRequestHandler,HTTPServer
import socketserver
import threading

from os import curdir, sep
import os
PORT_NUMBER = 80

#This class will handles any incoming request from
#the browser 
class myHandler(BaseHTTPRequestHandler):
	
	#Handler for the GET requests
	def do_GET(self):
		if self.path=="/":
			self.path= os.path.join("http_server","templates","index.html")

		try:
			#Check the file extension required and
			#set the right mime type

			sendReply = False
			if self.path.endswith(".html"):
				mimetype='text/html'
				sendReply = True
			if self.path.endswith(".jpg"):
				mimetype='image/jpg'
				sendReply = True
			if self.path.endswith(".gif"):
				mimetype='image/gif'
				sendReply = True
			if self.path.endswith(".js"):
				mimetype='application/javascript'
				sendReply = True
			if self.path.endswith(".css"):
				mimetype='text/css'
				sendReply = True
				self.path= os.path.join("http_server","static","main.css")


			if sendReply == True:
				#Open the static file requested and send it
				path = os.path.join(os.getcwd(),self.path)
				found = os.path.isfile(path)
				print("{} file {}: ".format("founded" if found else "didnt find",path)) 
				#f = open(os.path.join(os.getcwd(),self.path)) 
				f = open(curdir + sep + self.path) 
				self.send_response(200)
				self.send_header('Content-type',mimetype)
				self.end_headers()
				self.wfile.write(bytes(f.read().encode('UTF-8')))
				f.close()
			return


		except IOError:
			self.send_error(404,'File Not Found: %s' % self.path)



def start_http_server(port):
	server = HTTPServer(('', port), myHandler)
	print ('Started httpserver on port ' , port)
	thread = threading.Thread(name="http server",target=server.serve_forever)
	thread.daemon = True
	thread.start()
	





from livereload import Server, shell

server = Server()

server.watch("docs/*.rst", shell("make docs"))
server.serve(root="public/")

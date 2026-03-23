# Pylon

A lightweight HTTP server framework built from scratch in Python using raw TCP sockets.

# Motivatoin

Most backend tutorials teach you framework syntax, not how things actually work. `@app.route` appears and a request magically shows up in your handler. What happened in between stays hidden behind layers of abstraction.

I wanted to kill that magic. What actually happens when a browser sends a request? What does the raw data look like? What _is_ HTTP underneath all the frameworks?

So I built **Pylon** — an HTTP server from a raw TCP socket up, no libraries doing the hard parts. By the end I had read real HTTP bytes off a TCP connection, parsed them by hand, built a routing system, and written a response builder from scratch.

The magic was gone. That was the whole point.

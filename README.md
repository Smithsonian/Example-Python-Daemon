# Example-Python-Daemon

Based on tutorial at https://alexandra-zaharia.github.io/posts/stopping-python-systemd-service-cleanly/

Service is set up to use `SIGINT` to safely stop the process.  This is caught within the service event loop by `except KeyboardInterrupt:`, allowing closing of open pipes and files, and other shutdown procedures to be called.

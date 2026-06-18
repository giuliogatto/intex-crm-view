Application architecture.
There are 3 main components in the architecture, all 3 of them isolated in a docker compose file and all belonging to the same docker network for intercommunincation. Each container exposes its own port to the local host. 

data component in /data folder.
holds a timescaledb (postgreqsl) database with a dedicated /data/data persistance volume.
it runs the create-tables.sql migrations whenever it's rebuilt.

backend component in /backend folder.
holdes a python bottle backend application called index-api with hot reload and connects to the database using database.py.

frontend
holds the frontend vite/react application with its own nginx config

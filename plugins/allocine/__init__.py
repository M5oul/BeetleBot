from . import allocine
from plugin import Plugin
import json
from xml.sax.saxutils import escape
import datetime


class Allocine(Plugin):
    def __init__(self, core):
        super().__init__(core)
        self.register_command('movies', self.print_movies)


    def print_movies(self, time=None):
        """ Usage: !movies [today|YYYY-MM-DD]"""
        movies, chosen_time = allocine.get_movies(time)
        chosen_time = datetime.datetime.strptime(chosen_time, "%Y-%m-%d")
        message = "Movies for %s" % chosen_time.strftime("%A, %b %d %Y\n\n")
        for theater, movies in movies.items():
            if not movies:
                continue
            message += "\n" + escape(theater) + ":\n"
            for movie, infos in sorted(movies.items(), key=lambda x: x[1]['vo']):
                message += "\t"
                if infos['vo']:
                    message += "<span style='color: green'> VO </span>"
                message += escape(movie)
                for hour in infos['times']:
                    message += "<span style='color: orange'> [" + hour + "]</span>"
                message += "\n"
        if not message:
            message = "No movies :/"

        self.send_message_to_room(message)


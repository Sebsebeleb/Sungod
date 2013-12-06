    # -*- coding: utf-8 -*-

import sys
import traceback
import os
sys.path.append(os.path.join("libs", "external"))

import pickle as cPickle  # @UnusedImport HAHAHHAHAH LEARN TO USE IMPORTS PROPERLY
import random
import datetime
import re
import urllib
import shelve
import time
from collections import deque
import threading
from subprocess import call

import irc.client as irclib
import feedparser
from BeautifulSoup import BeautifulSoup
import wikipedia
# from libs.external import ConfigParser
import ConfigParser  # should be in external
import html2text

from libs import PyNify
from libs import arena
from libs import math_parse
# import libs.reddit as reddit
import math

htmlre = re.compile(
    r"\S+\.\S+")  # shouldn't these be wrapped in an anymous, self-referencing function call?
spotre = re.compile(r"spotify:track:([A-Za-z0-9]{22})")
rusre = re.compile(r"\)")
teutre = re.compile(r"gut|bat|rut")
re_crossdress = re.compile("xD")
re_note = re.compile(r"[N|n]ote to (\S+):(.+)")

re_scale = re.compile(r"(|.+ )(((?P<low1>\d+)-(?P<high1>\d+))|((?P<low2>\d+) to\
                      (?P<high2>\d+)))")
songre = re.compile(r"og:title\" content=\"(.*)\"")
artre = re.compile(r"artist/[A-Za-z0-9]{22}\">(.*)</a>")

re_math = re.compile(r"([0-9-+/\*^\(\)]|"+"|".join(dir(math))+")+")
re_because = re.compile(r"[B|b]ecause (.+)")

random.seed()

pubcommands = {}

server = None
speaker = None


config = ConfigParser.ConfigParser()
config.read(r"conf.ini")  # read the config.ini
previous_line = ""

pie_jokes = (
    ("What's the best thing to put into a pie?", 'Your teeth!'),
    ('Why did the pie go to a dentist?', 'Because he needed a filling!'),
    ("What's the difference between a worm and an apple?",
        'Have you ever tried worm pie?'),
    ('What do you get if you cross a jogger with an apple pie?',
     'Puff pastry'),
    ('What did the cherry say to the cherry pie?', "You've got some crust."),
    ('Where does Dorothy from OZ weigh a pie?',
        'Somewhere over the rainbow, weigh-a-pie!'),
    ("What is a ghost's favourite dessert?", 'Boo-Berry pie with I-scream!'),
    ("What did the boss say to the bad employee?", "You're pie-red!"),
    ("What do you call a religious baker?", "pie-ous."),
    ("Which programming language is the tastiest?", "Piethon."),
    ("What is the baker's favorite game?", "Pierim."),
    ("What material are bakeries made of?", "Pie-n wood."),
    ("Why did the wounded ask for painkillers?",
     "It was too pienful for him."),
    ("How do you measure large quantities of pies?", "In piels"),
    ("What is my weapon of choice?", "Piek"),
    ("What hot and piery hero is my favorite?", "Piero"),
    ("What is the name of united tribes?", "Empieres"),
    ("Mathematician: Pi r squared", "Baker: No! Pie are round!"),
    ("Question: What do you get if you divide the circumference of a jack-o-lantern by its diameter?",
     "Answer: Pumpkin Pi!"),
    ("The roundest knight at Sir Arthur's table was Sir Cumference. He gained weight by eating too much Pi"),
    ("What part of a fish weighs the most?", "Its scales!"),
    ("Which fish love being naked?", "Bare-a-cudas!"),
    ("What do you call a fish with no eye?", "Fssshh"),
    ("Why are fish so intelligent?", "Because they swim in schools!"),
    ("Why do fish not like basketball?",
     "Because they are afraid of the net!"),
    ("What is the best way to communicate with a fish?", "Drop it a line!"),
    ("Two fish swim into a concrete wall.",
     "The one turns to the other and says 'Dam!'"),
    )


connection_info = {
    "network": config.get("connection", "network"),
    "port": int(config.get("connection", "port")),
    "channel": config.get("connection", "channel"),
    "nick": config.get("connection", "nick"),
    "name": config.get("connection", "name"),
    "prefix": config.get("connection", "prefix"),
    "nickservpass": config.get("connection", "nickservpass"),
    }

stats = {

    "LINKMAXTITLE": 28,
    "PEEKMAXTITLE": 64,
    "smart_mode": True,
    "peek_mode": True,
    "immortal": True,
    "debug": False,
    "log_length": 100,
    "arena_enabled": True,

    "users": {},
    "pub_commands": {},
    "pvt_commands": {},
    "links": [],
    "traceback": False,
    "autosave_interval": 60,
    "spell_dict": "en-BE",
    "rss": {"last": time.gmtime(),
            "interval": 120,
            "feeds": [r"http://www.gamer.no/feed/rss/",
                      r"http://api.twitter.com/1/statuses/user_timeline.rss?screen_name=BadlybadGames",
                      r"http://bbg.terminator.net/forums/syndication.php?limit=15"
                      ]},
    "git": {"tag": None},
    }

smart_memory = {"why": []}

log = deque(maxlen=stats["log_length"])

hooks = []


class Error(Exception):

    """Base class for exception in this module"""
    pass  # the salt, please


class ArgsError(Error):

    def __init__(self, expr, msg):
        self.expr = expr
        self.msg = msg

#erstatter urlopen med custom-versjon som bruker w0bbrowser-headers!
class sneakyurl(urllib.FancyURLopener):
    version = "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/31.0.1650.57 Safari/537.36 OPR/18.0.1284.49"
urllib._urlopener = sneakyurl()

class User(object):

    def __init__(self, name):
        self.name = name
        self.power = 100
        self.lines = 0
        self.sin = 0
        self.rusness = 0
        self.batness = 0
        self.crossdressness = 0
        self.faith = 0
        self.links = 0
        self.checked_notes = True
        self.hero = None
        self.charges = 0
        self.last_line = ""
        self.previous_line = ""

    @classmethod
    def update_user(cls, old):
        new = cls(old.name)
        for i in dir(old):
            if hasattr(new, i):
                setattr(new, i, getattr(old, i))
        return new

#
# Internal Commands
#


def temp_pub(command, timeout):
    """
    Will make :command be called with message on pub message while active
    (until timeout is reached)
    """
    server.add_global_handler("pubmsg", command, 100)
    server.execute_delayed(irc.remove_global_handler, command, timeout)


def register_func(f):
    print irc
    irc.add_global_handler('pubmsg', f)

#
# IRC Commands
#


class basecmd():
    type = "pub"
    powerreq = 100
    trigger = None

    @classmethod
    def do(cls, connection, event):
        connection.privmessage(event.target, "Sorry, unimplemented")

    def __repr__(self):
        return "%s:%s" % (self.trigger, self.powerreq)


class Ninjafy(basecmd):
    type = "pub"
    trigger = "ninjafy"

    mapping = {"a": "ka", "b": "zu", "c": "mi",
              "d": "te", "e": "ku", "f": "lu", "g": "ji",
   "h": "ri", "i": "ki", "j": "zu", "k": "me", "l": "ta",
   "m": "rin", "n": "to", "o": "mo", "p": "no", "q": "ke",
   "r": "shi", "s": "ari", "t": "chi", "u": "do", "v": "ru", "w": "mei",
   "x": "na", "y": "fu", "z": "zi", " ": " ", "?": "??"}

    def do(self, args, connection, event):
        name = " ".join(args)
        name = [i.lower() in self.mapping.keys()
               and i.lower() or "?" for i in name]
        say("".join([self.mapping[i]
            for i in name]).capitalize(), event.target)


class wobHere(basecmd):
    type = "pub"
    trigger = "wobHere"

    def do(self, args, connection, event):
        say(event.target, connection.whois("w0bni"))


class Week(basecmd):
    type = "pub"
    trigger = "week"

    def do(self, args, connection, event):
        week = datetime.date.today().isocalendar()[1]
        connection.privmsg(event.target, "The current week is: " + str(
            week) + ", aka "+["B", "A"][week % 2]+"-uke.")


class Pynify(basecmd):

    """(url), returns a short url"""
    type = "pub"
    trigger = "tinyfy"

    def do(self, args, connection, event):
        try:
            result = PyNify.tinyfy("".join(args))
            print "Here is result: "+str(result)
        except:
            result = "Sorry, error occoured."
        else:
            connection.privmsg(
                event.target, "Here is your short url, smallson: " + str(result))


class Statsmanip(basecmd):

    """([user], stat, new), modifies the stats data"""
    type = "pub"
    trigger = "set"
    powerreq = 2

    print stats["users"]

    def do(self, args, connection, event):
        try:
            if len(args) == 3:
                u, s, v = args
            elif len(args) == 2:
                s, v = args
                u = False
            else:
                say("Sorry, I need 2 or 3 arguments", event.target)
            speaker = event.source  # .split('!') [0]

            if u in stats["users"].keys():

                if s == "power" and int(v) < stats["users"][speaker].power and speaker.lower() != "sebsebeleb":
                    connection.privmsg(event.target, "OH NO YOU DIDNT!")
                    return
                try:
                    setattr(stats["users"][u], s, eval(v))
                    print "Setting " + str(u) + "'s " + str(s) + " to " + str(v)
                except AttributeError:
                    print "User did not have this stat before."
                except KeyError:
                    connection.privmsg(
                        event.target, "Sorry, user '" + u + "' not found.")
                except Exception as e:
                    print e

                else:
                    stats[s] = v
            else:
                print "Setting global stat"
                stats[s] = eval(v)

        except ValueError as e:
            print e
            connection.privmsg(event.target, "Syntax error")


class Get(basecmd):

    """([user], stat), retrieves data"""
    powerreq = 3
    trigger = "get"

    def do(self, args, connection, event):
        s = u = None
        if len(args) == 2:
            u, s = args
        elif len(args) == 1:
            s = args[0]
        else:
            say("Sorry, I need 1 or 2 arguments", event.target)

        if u:
            obj = stats["users"][u]
            atr = getattr(obj, s)
        else:
            obj = stats
            atr = stats[s]

        say(atr, event.target)


class JoinChan(basecmd):

    """(#channel), Joins the specified channel"""
    trigger = "join"
    powerreq = 5

    def do(self, args, connection, event):
        server.join(args[0])


class PartChan(basecmd):

    """(channel, [message]) Leaves the channel specified"""
    trigger = "leave"
    powerreq = 5

    def do(self, args, connection, event):
        target = args[0]
        leave_message = "" if len(args) == 1 else " ".join(args[1:])

        server.part(target, leave_message)


class Query(basecmd):

    """(channel|user, msg) Tells the specified channel/user message"""
    trigger = "tell"
    powerreq = 20

    def do(self, args, connection, event):
        target = args[0]
        message = " ".join(args[1:])
        connection.privmsg(target, message)


class Quote(basecmd):

    """([quote]/list) Tells the story of [quote], or if no quote, a random quote """
    trigger = "quote"
    powerreq = 100
    quotes = {"bsmith noob":
            ["[20:03] <Sungod> .bsmith lol noob",
            "[20:03] <bsmith> Sungod, Looking good",
            "[20:03] <Sungod> Not sure what you are trying to say!"
             ],
            "pierim": [
                "Sebtop: then there is NO way YOU CANT buy Skyrim",
                "Sebtop: its like liking food and never eating pie",
                "w0bni: 200kr worth it?",
                "Sebtop: ofcourse, like paying 10 kr for a pie made by world's best pie cook",
                "w0bni: how do I pronounce it?",
                "Sebtop: Pierim"
            ],
        "fishes": ["<Frets> Sungod, how can we cheer you up?",
            "<Sungod> Sleep with the fishes"
                       ],
            "woman": ["<Danvari> Sungod, what is a woman?",
            "<Sungod> Run away"
                      ],
            "danbad": ["[19:08] <Frets> Sungod, why is Dan so bad?",
            "[19:08] <Sungod> Check with Sebsebeleb has great knowledge regarding that"
                       ],
            "Tapion neutralizes Nekromans": [
                "[12:32] <Tapion> Sungod /convert nekromans",
                "[12:32] <Sungod> Succesfully executed command]",
                "<i>And thus, the eternal struggle was solved.</i>"
            ],
        "w0bni's special sauce": [
            "<w0bni> oh wow",
            "<w0bni> my special sauce all over the monitor",
            ]
        }

    def do(self, args, connection, event):
        args = " ".join(args).strip("'\"")

        quote = None
        if args == "list":
            connection.privmsg(event.target, "Available quotes:")
            connection.privmsg(event.target, '"' + '", "'.join(
                self.quotes.keys())+'"')

        elif args in self.quotes.keys():
            quote = self.quotes[args]
        else:
            quote = self.quotes[random.choice(self.quotes.keys())]

        if quote:
            connection.privmsg(
                event.target, "Let me tell you a story, youngster. It was a sunny day, when this was said...")
            for x in quote:
                connection.privmsg(event.target, x)


class RandomQuote(basecmd):
    trigger = "randommsg"

    def do(self, args, connection, event):
        print "Sorry, I no longer track your actions."
        return

        if len(args) > 1:
            try:
                n = int(args[1])
            except ValueError:
                connection.privmsg(event.target, "Invalid argument!")
                return
        elif len(args) == 0:
            connection.privmsg(event.target, "I need arguments!")
            return
        else:
            n = 1
        try:
            u = args[0]
            print random.randrange(stats["users"][u].lines_spoke)
            quotes = [stats.users[u].lines[random.randrange(
                len(stats.users[u].lines))] for x in range(n)]
        except IndexError:
            connection.privmsg(event.target, "No user named '" + args[0] + "'")
            return

        for q in quotes:
            connection.privmsg(event.target, u + ": " + q)


class Roll(basecmd):
    trigger = "roll"


class gw2check(basecmd):
    trigger = "gw2check"

    def do(self, args, connection, event):
        prop = os.popen("C:/WINDOWS/system32/tasklist.exe", "r")
        proclist = prop.readlines()
        prop.close()

        response = "The dragon is gone! Quick, exploit his treasure before he returns!"
        for process in proclist:
            if "Gw2.exe" in process:
                response = "The dragon is guarding his treasure. You will have to wait."

        connection.privmsg(event.target, response)


class TopSpeakers(basecmd):
    trigger = "topspeakers"

    def do(self, args, connection, event):
        n = 5
        if not len(args):
            pass
        else:
            try:
                n = int(args[0])
            except IndexError:
                connection.privmsg(event.target, "Bad arg.")

        connection.privmsg(event.target, (
            "Top speakers of " + event.target).center(45, "*"))
        for rank, u in enumerate([i[1] for i in reversed(sorted(stats.users.items(), key=lambda t: t[1].lines_spoke))][:n]):
            connection.privmsg(event.target, ((("   %s. is %s with %s lines" % ((
                rank+1, u.name, u.lines_spoke))).ljust(35, " ")).center(45, "*")))


class TopWord(basecmd):
    trigger = "topwords"

    def do(self, args, connection, event):
        if len(args) > 1:
            try:
                n = int(args[1])
            except ValueError:
                connection.privmsg(event.target, "Invalid argument!")
                return
        else:
            n = 1
        try:
            u = args[0]
        except:
            pass


class DisplayHelp(basecmd):
    trigger = "help"

    def do(self, args, connection, event):
        connection.privmsg(event.target, "Possible commands: " + str(list(
            c for c in reversed(sorted(pubcommands.values(), key=lambda t: t.powerreq)))))


class DaysTG(basecmd):

    """() Displays the time untill TG"""
    trigger = "tg"

    tgtime = datetime.datetime(2013, 4, 4, 9)

    def do(self, args, connection, event):
        now = datetime.datetime.now()
        difference = self.tgtime-now
        connection.privmsg(event.target, str(difference).partition(".")[0])


class DFmoral(basecmd):
    trigger = "df"

    def do(self, args, connection, event):
        site = urllib.urlopen(
            "http://df.magmawiki.com/index.php/Main_Page").read()
        rex = re.compile(
            r'<div style="float: right; margin-left: 1em"><div style=.+>(.+)</div></div>')
#        l = True
#        while l != "":
#            l = "".join([site.readline(),site.readline(),site.readline(),site.readline()])
#            m = re.findall(rex,l)
#            print "EMMMM: ", m,"\n\n\n"
#            if m:
        match = rex.search(site)
        if match:
            connection.privmsg(event.target, match.groups()[0])
            return
        else:
            connection.privmsg(event.target, "Sorry, something is wrong.")


class Random(basecmd):
    _heroes = ['Emerald Warden', 'Nomad', 'Devourer', 'Valkyrie', 'Amun Ra',
        'Flint Beastwood', 'Pandamonium', 'Midas', 'Torturer', 'Legionnaire',
        'Myrmidon', 'Lord Salforis', 'Rampage', 'Swiftblade', 'Electrician',
        'Predator', 'Scout', 'Witch Slayer', 'Armadon', 'Pyromancer',
        'Dampeer', 'Magebane', 'Monarch', 'Pebbles', 'Fayde', 'Aluna', 'Plague Rider',
        'Succubus', 'Flux', 'Zephyr', 'Accursed', 'Blood Hunter',
        'Gemini', 'Magmus', 'Moraxus', 'Parasite', 'Wretched Hag',
        'Thunderbringer', 'Monkey King', 'Tempest', 'Chronos',
        'Night Hound', 'Slither', 'Deadwood', 'Pollywog Priest',
        'Forsaken Archer', 'Demented Shaman', 'Kraken', 'Arachna',
        'Glacius', 'Wildsoul', 'Moon Queen', 'Blacksmith', 'Nymphora',
        'Engineer', 'Corrupted Disciple', 'Gauntlet', 'Bubbles', 'Voodoo Jester',
        'Pharaoh', 'Vindicator', 'Jeraziah', 'Hellbringer', 'The Gladiator',
        'Silhouette', 'Hammerstorm', 'Pestilence', 'Behemoth', 'Puppet Master',
        'Keeper of the Forest', 'Master Of Arms', 'Cthulhuphant', 'Bombardier',
        'Soulstealer', 'Maliken', 'Andromeda', 'The Madman', 'Martyr', 'Drunken Master',
        'Tremble', 'The Chipper', 'Empath', 'Soul Reaper', 'Tundra', 'Defiler',
        'Revenant', 'Rhapsody', 'Sand Wraith', 'Doctor Repulsor', 'Geomancer',
        'War Beast', 'The Dark Lady', 'Balphagore', 'Ophelia', 'Shadowblade']
    _hero = _heroes
    _support = ["Midas (semi)", "Myrmidon", "Witch Slayer", "Pyromancer",
        "Monarch", "Plague Rider", "Succubus", "Accursed", "Magmus", "Thunderbringer (semi)",
        "Tempest", "Slther", "Pollywog Priest", "Demented Shaman", "Glacius",
        "Blacksmith", "Nymphora", "Engineer", "Bubbles (semi)", "Voodoo Jester",
        "Pharaoh (situ)", "Vindicator", "Jereziah", "Hellbringer", "Hammerstorm (semi)",
        "Behemoth (semi)", "Bombardier (semi)", "Andromeda", "Martyr (semi)",
        "Empath", "Soul Reaper (situ)", "Revenant", "Rhapsody", "Geomancer",
        "Ophelia"]
    _w0bstyle = [
        "Enigma", "Rikimaru", "Roshan", "Slather", "Chokochick", "Batni",
        "Shrut", "Codex 5", "SotM NH", "Slothni", "Codex Queen", "Fundromeda", "Pesto",
        "Etter", "Titstandul", "HERREX!!!!", "Funarch"]
    _pusher = [
        "Tempest", "Keeper of the Forest", "Pollywog", "Torturer", "Balphagore",
        "Hellbringer (semi)", "Demented shaman (semi)", "Rhapsody (semi)", "Soul reaper",
        "Parasite (semi)", "Legionaire (cskip)", "Zeph (cskip)"]
    _push = _pusher
    _nuker = ["Pyromancer", "Torturer",
        "Thunderbringer", "Behemoth", "Wretched hag"]
    _ganker = [
        "Pyromancer", "Torturer", "Thunderbringer", "Behemoth", "Wretched hag",
        "Tempest", "Deadwood", "Devourer", "Valkyrie", "Pandamonium", "Electrician", "Gauntlet",
        "Pestilence", "Andromeda", "Tundra", "Geomancer", "Doctor Repulsor", "Succubus"]
    _hard_carry = [
        "Madman", "Chronos", "Swiftblade", "Moon Queen", "Wild Soul", "Puppet Master",
        "Vindicator", "Soulstealer", "Night Houn", "Gemini", "Dampeer", "Soul Reaper"]
    _kongor = [
        "Wild Soul", "Valkyrie", "Gauntlet", "Slither", "Pharaoh", "Plague Rider",
        "War Beast", "Demented Shaman"]
    _healer = [
        "Soul reaper", "Nymphora", "Demented shaman", "Jereziah", "Monarch",
        "Martyr", "Empath", "Accursed", "Midas", "Rhapsody", "Ophelia"]
    _heal = _healer
    _kong = _kongor
    _kong1 = _kongor
    trigger = "random"
    number = random.randint
    num = number
    roll = lambda self, x, y: random.randint(int(x), int(y))
    validargs = ["heroes", "nuker", "w0bstyle",
        "push/pusher", "heal(er)", "hard_carry", "kongor"]
    _user = property(lambda self: [i for i in getattr(stats, "users").keys()])
    bool = property(lambda self: random.random() > 0.5 and "Yes" or "No")

    def _randhero(self, l):
        return random.choice(getattr(self, "_"+l))

    def do(self, args, connection, event):
        times = 1
        print args
        if len(args) == 0:
            say(event.target, "I require an argument!")
            return
        if "*" in args[-1] and re.search("\d$", args[-1]):
            times = int(re.search("\d", args[-1]).group(0))
            args.pop()
        print times

        print "args:", args

        try:
            if len(args) == 0:
                connection.privmsg(event.target, "I Require an argument!")
                return
            elif args[0] == "?":
                connection.privmsg(event.target, self.validargs)
                return
            elif len(args) == 1:
                try:
                    if times > len(getattr(self, "_"+args[0])):
                        times = len(getattr(self, "_"+args[0]))
                    result = []
                    h = self._randhero(args[0])
                    for i in range(times):
                        while h in result:
                            h = self._randhero(args[0])
                        result.append(h)
                except:
                    result = []
                    for i in range(times):
                        result.append(getattr(self, args[0]))
            else:
                result = []
                for i in range(times):
                    result.append(getattr(self, args[0])(*args[1:]))
        except Exception as e:
            connection.privmsg(event.target, "Sungod does not comprehend.")
        else:
            print result
            if times > 1:
                connection.privmsg(event.target, "Sungod chooses... " + ", ".join(
                    result[:-1]) + " and " + result[-1] + "!")
            else:
                connection.privmsg(
                    event.target, "Sungod chooses... " + result[0])


class Timer(basecmd):

    """([who], time, [message]), after the specified time has passed, will deliver the message to the specified person, or you"""
    trigger = "timer"

    def _remind(self, target, channel, message, connection):
        s = target + " wake up! " + message
        connection.privmsg(channel, s)
        connection.privmsg(target, s)
        connection.notice(target, s)

    def do(self, args, connection, event):
        speaker = event.source.split('!')[0]

        if args[0][0].isalpha():
            who = args[0]
        else:
            who = speaker
        print args

        delay = 0
        for a in [c for c in args if c[0].isdigit()]:
            i = re.match("\d+", a)
            i = int(i.group())
            f = 1
            if any([a.endswith(n) for n in ["d", "day", "days"]]):
                f = 60*60*24
            elif any([a.endswith(n) for n in ["h", "hour", "hours"]]):
                f = 60*60
            elif any([a.endswith(n) for n in ["m", "minute", "minutes", "min"]]):
                f = 60
            elif any([a.endswith(n) for n in ["mo", "month", "months"]]):
                f = 60*60*24*32
            elif any([a.endswith(n) for n in ["y", "year", "years"]]):
                f = 60*60*24*32*12
            delay += i * f

        trigger_date = datetime.datetime.now() + datetime.timedelta(0, delay)
        if who == speaker:
            s = "You"
        else:
            s = who
        s = s + " will be reminded at " + str(
            trigger_date.strftime("%d.%m.%Y %H:%M:%S"))
        connection.privmsg(event.target, s)

        message = re.search(r'".+"', " ".join(args))
        if not message:
            message = ""
        else:
            message = message.group()

        irc.execute_delayed(delay, self._remind, (
            who, event.target, message, connection))


class GetError(basecmd):
    powerreq = 100
    trigger = "get_error"

    def do(self, args, connection, event):
        print "Error: ", stats["error"]
        say(stats["error"], event.target)


class Restart(basecmd):
    trigger = "restart"

    def do(self, args, connection, event):
        print "HELLO"
        proc = sys.executable
        server.disconnect()
        call(["git", "pull", "origin"])
        os.execl(proc, proc, * sys.argv)


class RPS(basecmd):
    TIMEOUT = 8
    trigger = "rps"
    players = []
    players_wait = []
    answers = {}
    active = False

    def do(self, args, connection, event):
        """Arguments:
        Player(req), player to challenge
        Rounds(1), rounds to play
        """

        if self.active:
            connection.privmsg(
                event.target, "Sorry, another game is already going on")
            return
        try:
            if not len(args) == 1 and not len(args) == 2:
                connection.privmsg(event.target, "Your arguments are invalid.")
                return
            elif len(args) == 2:
                user, Rounds = args[0], int(args[1])
            else:
                user, rounds = "".join(args), 1

        except Exception as e:
            print e
            connection.privmsg(event.target, "I do not understand")

        self.active = True
        irc.add_global_handler("pubmsg", self.on_talk, -1)
        irc.execute_delayed(self.TIMEOUT, self._deactivate, [event.target])
        self.players = [user.lower(), event.source.split('!')[0].lower()]
        print self.players
        self.players_wait = list(self.players)

        for u in self.players:
            a = range(1, 4)
            random.shuffle(a)
            self.answers[u] = a
            print a
            connection.notice(
                u, "Choose wisely!; Rock: %s,Paper: %s, Scissor: %s" % tuple(a))

    def _deactivate(self, target):
        print "deactivating!"
        print self.active, len(self.players_wait)
        if self.active:
            say("Game timed out", target)
            self.active = False
            self.players = []
            self.players_wait = []
            self.answers = {}

    def on_talk(self, connection, event):

        msg = event.arguments[0]
        speaker = event.source.split('!')[0].lower()
        if speaker in self.players_wait and msg in ["1", "2", "3"]:
            self.players_wait.remove(speaker)
            self.answers[speaker] = ["Rock", "Paper", "Scissors"][
                self.answers[speaker].index(int(msg)-1)]
            print self.players_wait
            if len(self.players_wait) == 0:
                print "It is!"
                irc.remove_global_handler("pubmsg", self.on_talk)
                self.finish(connection, event.target)
        else:
            return

    def finish(self, connection, target):
        winner = False
        print self.answers
        p1 = self.answers.keys()[0]
        p2 = self.answers.keys()[1]
        p1a = self.answers[p1]
        p2a = self.answers[p2]
        print "ANSWERS: " + p1a + " " + p2a
        if p1a == "Rock" and p2a == "Paper":
            winner = p2
            a = "R<P"
        elif p1a == "Rock" and p2a == "Scissors":
            winner = p1
            a = "R>S"
        elif p1a == "Paper" and p2a == "Rock":
            winner = p1
            a = "P>R"
        elif p1a == "Paper" and p2a == "Scissors":
            winner = p2
            a = "P<S"
        elif p1a == "Scissors" and p2a == "Rock":
            winner = p2
            a = "S<R"
        elif p1a == "Scissors" and p2a == "Paper":
            winner = p1
            a = "S>P"
        else:
            winner = "no one :("
            a = False
        if a:
            connection.privmsg(
                target, "And the winner is... " + winner + "(" + a + ")")
        else:
            connection.privmsg(target, "And the winner is... " + winner)
        self.active = False


class Exec(basecmd):
    trigger = "exec"
    powerreq = 1

    def do(self, args, connection, event):
        command = " ".join(args)
        print command
        try:
            exec(command)
        except Exception as e:
            connection.privmsg(event.target, "You are talking unclear.")
            print e


class Python(basecmd):
    trigger = "python"
    powerreq = 50

    def do(self, args, connection, event):
        try:
            equation = " ".join(event.arguments[0].split(" ")[2:])
            if "open(" in equation:
                result = "Don't you dare, dear!"
            result = eval(equation)
        except Exception as e:

            result = "Sorry, error: ", e[:30]
        if result:
            connection.privmsg(event.target, result)


class Die(basecmd):
    trigger = "die"
    powerreq = 0

    def do(self, args, connection, event):
        save_settings()
        sys.exit("Killed gracefully")


class Spell(basecmd):

    trigger = "spell"
    commands = ["set", "get"]

    def do(self, args, connection, event):
        import enchant
        d = enchant.Dict(stats["spell_dict"])
        if args[0] in self.commands:
            pass
        else:
            if len(args) > 1:
                failed = False
                s = list(args)
                for i, a in enumerate(args):
                    if not d.check(a):
                        s[i] = d.suggest(a)[0]
                        failed = True

                print failed

                if not failed:
                    connection.privmsg(event.target, "Correctly spelled")
                    return
                else:
                    connection.privmsg(
                        event.target, "Spelling error, (" + " ".join(s) + ")")
            else:
                a = args[-1]
                s = (d.check(a) and "Found " or "Not found ") + \
                    "related: " + ", ".join(d.suggest(a))
                connection.privmsg(event.target, s)


class Charges(basecmd):

    """
    One charge regenerations every test, max of 2.
    """
    trigger = "charges"

    def do(self, args, connection, event):
        if not ("w0bni" in stats["users"]):
            connection.privmsg(
                event.target, "w0bni is clouded before my eyes!")
            return
        w = stats["users"]["w0bni"]
        if speaker != "Frets" and args[0] not in ["get", "check", "remaining"] and args[0] in ["add", "remove"]:
            if speaker == "w0bni":
                connection.privmsg(
                    event.target, "GOOD TRY MADS. Sin increased by 1")
                stats["users"]["w0bni"].sin += 1
            else:
                connection.privmsg(event.target, "Sorry, you arent Frets.")
        else:
            try:
                cmd = args[0]
                if cmd == "remove":
                    w.charges -= 1
                    if w.charges < 0:
                        connection.privmsg(
                            event.target, "w0bni did not have any charges at the moment.")
                        w.charges = 0
                elif cmd == "add":
                    w.charges += 1
                    if w.charges > 2:
                        w.charges = 2
                        connection.privmsg(
                            event.target, "w0bni already had max amount of charges")
            except AttributeError as e:
                    print e
                    connection.privmsg(
                        event.target, "w0bni did not have charges leveled up, leveling it up for him...")
                    w.charges = 1
        if args[0] in ["get", "check", "remaining"]:
            connection.privmsg(event.target, "w0bni has " + str(
                w.charges) + " left at the moment.")


class Dictionary(basecmd):
    trigger = "define"

    def do(self, args, connection, event):
        import libs.dictionary as dictionary
        dictionary.load_index()
        d = dictionary.look_up(" ".join(args))
        print "d: ", d
        if not d:
            import enchant
            d = enchant.Dict(stats["spell_dict"])
            s = "'" + " ".join(args) + "' was not found, maybe you meant; " + ", ".join(
                d.suggest(" ".join(args))) + "?"
            connection.privmsg(event.target, s)
        else:
            for i in d:
                connection.privmsg(event.target, i)


class wob(basecmd):

    trigger = "wob"

    def do(self, args, connection, event):
        response = "Not quite shure!"

        getWobStatus = urllib.urlopen("http://198.199.126.196/wobcheck.php")
        wobStatus = str(BeautifulSoup(getWobStatus)).split("|")

        response = ("I am so sorry, " if wobStatus[
                    0] == "0" else "Indeed, ") + wobStatus[1]
        connection.privmsg(event.target, response)


class Top(basecmd):
    trigger = "top"

    def do(self, args, connection, event):
        stat = None
        n = 5
        reverse = True
        stat = args[0]
        if len(args) == 1:
            pass
        elif "reversed" in args or "-r" in args:
            if len(args) == 3:
                n = int(args[1] != "reversed" or args[
                        1] == "-r" and args[1] or args[2])
            reverse = False
        else:
            try:
                n = int(args[1])
            except:
                return
        if not hasattr(stats["users"].values()[0], stat):
            connection.privmsg(
                event.target, "Sorry, '" + stat+"' is not known to me")
            return
        l = [(i.name, getattr(i, stat)) for i in stats["users"].values()]

        l = sorted(l, key=lambda x: x[1])
        if reverse:
            l = [i for i in reversed(l)]

        l = l[:n]

        title = "Top " + stat + " of " + event.target + ":"
        connection.privmsg(event.target, title.center(
            len(title)+12, " ").center(55, "*"))
        if reverse:
            l = [(r, i[0], i[1]) for r, i in enumerate(l, 1)]
        else:
            l = [(len(stats["users"].values()) - r+1, i[0], i[1])
                for r, i in enumerate(l, len(stats["users"]))]
        for rank, user, value in l:
            connection.privmsg(event.target, (((("*"*5+" "*5+("%s. is %s with %s %s" % (
                rank, user, value, stat)))).ljust(50, " ")).ljust(55, "*")))


class RSS(basecmd):
    trigger = "rss"
    cmds = {}
    """
    add|delete string link
    """

    def do(self, args, connection, event):
        if len(args) < 2:
            connection.privmsg(event.target, "I require >2 arguments!")
            return
        if args[0] in self.cmds:
            print "\n\n\n", args, "\n\n\n\n"
            self.cmds[args[0]](*args)

    def add(self, link):
        stats["rss"]["feeds"].append(link)

    def delete(self, link):
        stats["rss"]["feeds"].remove(link)
    cmds = {"add": add, "delete": delete}


class UConvert(basecmd):

    """
    create_system name unitscale scaletype
    add_unit system long_name shortname scale_value
    convert value from_unit to_unit
    """
    trigger = "convert"

    def do(self, args, connection, event):
        try:
            result = unitconversion_middleway.do(args)
        except Exception as e:
            connection.privmsg(event.target, "Error: " + str(e))
        if result:
            s = "%s %s is %s %s" % (args[1], result[
                                    1].long_name, result[0], result[2].long_name)
        else:
            s = "Succesfully executed command"
        connection.privmsg(event.target, s)


class Time(basecmd):
    trigger = "time"

    def do(self, args, connection, event):
        minutes = datetime.datetime.now().minute
        index = int(round(minutes / 15.0))
        if index == 4:
            index = 0
        answer = ["It is HON O' CLOCK!", "It is quarter past HON TIME!",
            "It is half past HON TIME!", "It is quarter to HON TIME!"][index]
        answer += " (http://bbg.terminator.net/timeserver)"
        connection.privmsg(event.target, answer)


class Wikipedia(basecmd):
    trigger = "wiki"

    def do(self, args, connection, event):
        command, args = args[0], args[1:]
        print repr(str(command))
        print repr(args)
        s = getattr(wikipedia, str(command))(*args)
        s = s[:200]
        say(s, event.target)


builtincmds = [Statsmanip, JoinChan, PartChan, Query, Quote, DisplayHelp,
              RandomQuote, TopSpeakers, DaysTG, Random, RPS, Exec, Get,
              Timer, Die, Spell, Charges, Dictionary, Top, DFmoral, RSS,
              UConvert, Pynify, Python, Ninjafy, gw2check, GetError, Restart, Time,
              wob, Week, Wikipedia, wobHere]


class Hooks():

    temp_hooks = {}
    perma_hooks = []

    @classmethod
    def handle(cls, connection, event):
        """
        Handles the hooks. If the hook is used and wants to block, it will return
        true, signaling a block is wanted.
        """
        # print "temp hooks: ",cls.temp_hooks
        # print "perma hooks: ",cls.perma_hooks

        for i in cls.temp_hooks.keys():
            b = i(connection, event, cls.temp_hooks[i])
            if b:
                del cls.temp_hooks[i]
                return b

        for i in cls.perma_hooks:
            b = i(connection, event)
            if b:
                return b

    @classmethod
    def remove_hook(cls, hook):
        print "Removing hook: ", hook
        if hook in cls.temp_hooks:
            cls.temp_hooks.remove(hook)
            print "It was in temp hooks"
        elif hook in cls.perma_hooks():
            cls.perma_hooks.remove(hook)

    @classmethod
    def register_hook(cls, function, timeout=None, arguments=[]):
        print "I am registering hook for you."
        print function, timeout
        cls.temp_hooks[function] = arguments
        print cls.temp_hooks

    @classmethod
    def register_perma_hook(cls, function):
        cls.perma_hooks.append(function)


#
# Logic
#

def you_asked_memory(connection, event, asker):
    speaker = event.source.split('!')[0]
    message = event.arguments[0]

    if speaker == asker:
        sungod_says(message, connection, event, speaker)
        return True
    else:
        return False


def say(message, channel=connection_info["channel"]):
    connection_info["server"].privmsg(channel, message)


def handleJoin(connection, event):
    """
    Triggered when someone joins a channel?
    """
    if True:
        return
    print "|----ON JOIN INITIATE-----|"
    print event.source + " joined " + event.target
    print "Dir(event): ", dir(event)
    s = event.source
    print "Event.arguments: ", s
    joiner = event.source.split("!")[0]
    if joiner == connection_info["prefix"]:
        return
    print "joienr is: ", joiner
    print id(stats)
    print id(stats["users"][speaker]), " | ", repr(stats["users"][speaker])
    if joiner in stats["users"].keys():
        print "Joiner is in stats!"
        print "HAS THE USER CHECKED NOTES?: ", stats["users"][joiner].checked_notes
        if not stats["users"][joiner].checked_notes:
            print "joiner has not checked notes!"
            say("You have new notes, "+joiner+"! "+r"http://bbg.terminator.net/desknotes/notes/%s.txt" %
                joiner, event.target)
            # stats["users"][joiner].checked_notes = True
    print "|----ON JOIN GOODBYE-----|"


def handlePrivMessage(connection, event):
    speaker = event.source.split("!")[0]
    msg = event.arguments[0]
    tim = time.strftime("[%H:%M:%S]")
    print tim + '"'+speaker+'": ' + msg


"""def handlePrivMessage(connection, event):
    #THIS IS PRIVATE MESSAGE!!!
    speaker = event.source.split('!') [0]
    msg =  event.arguments[0]

    try: STATS.users[speaker.lower()].lines.append(msg)
    except KeyError:
        print "user " + speaker + " not recognized, creating"
        STATS.users[speaker.lower()].lines.append(msg)

    cmd,args = msg.split()[0],msg.split()[1:]

    print "Query> " + speaker + ": " + event.arguments[0]

    if cmd in pubcommands.keys():

        if int(STATS.users[speaker.lower()].power) <= int(pubcommands[cmd].powerreq) or speaker.lower() == "sebsebeleb":
            print pubcommands[cmd]
            pubcommands[cmd].do(args, connection, event)
        else:
            print "User tried to perform " +  cmd +", but his/her power isnt high enough (" + str(STATS.users[speaker].power) + " vs " + str(pubcommands[cmd].powerreq) + ")"
            connection.privmsg(event.source,"Sorry, not enough power.")

    elif any( d in msg for d in [ 'hello', 'hi', 'howdy', "morning", "hey", "hola", "greetings"] ):
        connection.privmsg(event.source, "Hello to you " + speaker + "!")
    elif msg == "kill":
        raise SystemExit
"""

#    else:
#        print "Command '" + cmd + "' not found. Possible commands: " + str(pubcommands.keys())
# connection.privmsg(event.source,"Not sure what you are trying to say!")


class Substitution():
    last = re.compile(r"last (\w+)")
    last_talker = re.compile(r"last_talker")

    @classmethod
    def convert(cls, s):
        print "Converting: ", s
        result = None
        log.reverse()
        match = cls.last.match(s)
        if match:
            for i in log:
                print "DEBUG: i: ", i
                if i[1] == match.groups()[0]:
                    print "IS! ", i
                    return i[0] + " " + i[1] + ": " + i[2]

        match = cls.last_talker.match(s)
        if match:
            return log[-1][1]

        log.reverse()
        if result:
            return result


def wiseWordsOfTheDay():
    wise = []


def update_stats(message, speaker):
    user = stats["users"][speaker]
    user.rusness += len(rusre.findall(message))
    if teutre.search(message):
        user.batness += 1
    user.crossdressness += len(re_crossdress.findall(message))


def handlePubMessage(connection, event):
    if event.target == "#sunfields" and stats["arena_enabled"]:
        arena.on_msg(connection, event)
        return
    global speaker
    speaker = event.source.split('!')[0]
    message = event.arguments[0]
    if speaker in stats["users"]:
        stats["users"][speaker].last_line = message
    time_stamp = time.strftime("[%H:%M:%S]")

    if "http://localhost" in message and "bni" in speaker:
        connection.privmsg(event.target, "He meant "+message.replace(
            "localhost", "84.215.30.88"))

    if "/bbgdump" in message:
        m = message.split("/bbgdump")[1].strip(" ")
        connection.privmsg(
            event.target, "http://bbg.terminator.net/media/dumps/"+m)

    l = message.split()
    message = " ".join([re.match(
        r"%(\w|_| )+%", i) and Substitution.convert(i)or i for i in l])

    global log
    log.append((time_stamp, speaker, message))

    if speaker not in stats["users"]:
        stats["users"][speaker] = User(speaker)
        if speaker == "Sebsebeleb":
            stats["users"][speaker].power = 0

    else:
        stats["users"][speaker].lines += 1

    if not stats["users"][speaker].checked_notes:
        stats["users"][speaker].checked_notes = True

    m = re_math.match(message)
    if m:
        result = math_parse.parse(message)
        say(result, event.target)

    link = htmlre.search(message)
    try:
        if link:
            stats["users"][speaker].links += 1
            link = link.group()
            link = link.startswith("http://") and link or "http://"+link
            site = urllib.urlopen(link)
            soup = BeautifulSoup(site)
            try:
                title = soup.find("title")
                title = title.string
                title = re.sub("(\n)|(  )", "", title)
            except Exception as e:
                print "ERROR OCCOURED: ", e
                title = None
            if stats["peek_mode"] and title:
                connection.privmsg(event.target, "'"+title[
                                   :stats["PEEKMAXTITLE"]]+"'")
    except:
        pass

    spot = spotre.search(message)
    try:
        if spot:
            spot = spot.groups()
            url = "http://open.spotify.com/track/"+spot[0]
            getInfo = urllib.urlopen(url)
            sup = BeautifulSoup(getInfo)
            if 'find that' in str(sup):
                connection.privmsg(
                    event.target, "That is _so_ not a working spotify URI.")
            else:
                artist = artre.findall(str(sup))
                song = songre.findall(str(sup))
                tags = song[0].split(" ")
                ulink = 'https://gdata.youtube.com/feeds/api/videos?orderby=viewCount&q=' + \
                    "+".join(tags)
                getTube = urllib.urlopen(ulink).read()
                countRes = getTube.split("totalResults>")[1].split("</")[0]
                if countRes == "0":
                    tubeOut = ""
                # elif artist in getTube: helt serr, få inn denne - det blir
                # kung. Statistikk basert på 2 testsøk viser det!
                else:
                    tubeOut = " (http://youtu.be/"+getTube.split(
                        "watch?v=")[1].split("&amp")[0]+")"
                    connection.privmsg(event.target, "" + str(
                        song[0])+" by "+str(artist[0]) + tubeOut)
    except:
        print "Spotify is bad."

    print event.target + '> ' + speaker + ': ' + event.arguments[0]

    # adds statistics
    update_stats(message, speaker)

    # Handle hooks
    if Hooks.handle(connection, event):
        return

    # LEARN!
    knowledge = re_because.search(message)
    if knowledge:  # then POWER
        smart_memory["why"].append(knowledge.groups()[0])

    if "dun " in message.lower():
        connection.privmsg(
            event.target, "http://www.youtube.com/watch?v=bW7Op86ox9g")

    elif message == "!":
        connection.privmsg(
            event.target, "http://www.youtube.com/watch?v=2P5qbcRAXVk")

    elif "ba dum" in message.lower():
        connection.privmsg(
            event.target, "http://www.youtube.com/watch?v=bcYppAs6ZdI")

    elif "excellent" in message.lower():
        connection.privmsg(
            event.target, "http://bbg.terminator.net/excellent.mp3")

    elif message.lower() == "no" and speaker.lower() == "blam":
        connection.privmsg(event.target, "http://bbg.terminator.net/no.mp3")

    elif message.lower() == "right" and speaker.lower() == "blam":
        connection.privmsg(event.target, "http://bbg.terminator.net/right.mp3")

    elif message.lower() == "absolutely" and speaker.lower() == "blam":
        connection.privmsg(
            event.target, "http://bbg.terminator.net/absolutely.mp3")

    elif message.lower() == "player" and speaker.lower() == "blam":
        connection.privmsg(
            event.target, "http://bbg.terminator.net/playah.mp3")

    elif "thai hoe" in message.lower() and speaker.lower() == "blam":
        connection.privmsg(
            event.target, "http://bbg.terminator.net/thai_hoe.mp3")

    elif message.lower() == "i say" and speaker.lower() == "blam":
        connection.privmsg(event.target, "http://bbg.terminator.net/isay.mp3")

    elif "smashing" in message.lower() and speaker.lower() == "blam":
        connection.privmsg(
            event.target, "http://bbg.terminator.net/smashing.mp3")

    elif "embarrasing" in message.lower() and speaker.lower() == "blam":
        connection.privmsg(
            event.target, "http://bbg.terminator.net/embarrasing.mp3")

    m = re.search(r"r/\w+", message, re.IGNORECASE)
    if m:
        connection.privmsg(
            event.target, "http://www.reddit.com/"+m.group().strip(" "))
    m = re.match(r"^s/(\w+)/(\w+)", message, re.IGNORECASE)
    if m:
        pat, rep = m.groups()
        message = stats["users"][speaker].previous_line
        s = re.sub(pat, rep, message)
        connection.privmsg(event.target, "He meant '"+s+"'")
    m = re.match(r"^a/(\w+)/(\w+)", message, re.IGNORECASE)
    if m:
        pat, rep = m.groups()
        message = previous_line
        s = re.sub(pat, rep, message)
        connection.privmsg(event.target, "He meant '"+s+"'")

    # Commands and Sungod say
    if event.arguments[0].lower().startswith(connection_info["prefix"].lower()):
        if "w0bni" in stats["users"]:
            stats["users"]["w0bni"].faith -= 1
            stats["users"]["w0bni"].sin += 1
        stats["users"][speaker].faith += 1
        msg = event.arguments[0][len(connection_info["prefix"])+1:].split()
        if len(msg) == 0:
            a = random.choice(
                ["What is the matter ", "Yes, ", "You seek my wisdom, ",
                             "Are the fishes troubling you, ", "Is the light unclear for your eyes, ",
                             "Is something the matter with your fishjumping, "])
            connection.privmsg(event.target, a + speaker + "?")
            Hooks.register_hook(you_asked_memory, 10, speaker)
            return

        cmd = msg[0]
        if len(msg) > 1:
            args = msg[1:]
        else:
            args = []

        if cmd[0] == "/":
            cmd = cmd[1:]
            if not cmd in pubcommands.keys():
                say("I do not understand what you want me to do", event.target)
                return

            if int(stats["users"][speaker].power) <= int(pubcommands[cmd].powerreq) or speaker.lower() == "sebsebeleb" or speaker.lower() == "w0bni":
                if len(args) > 0 and args[0] in ["help", "-h", "--help"]:
                    connection.privmsg(event.target, pubcommands[cmd].__doc__)
                else:
                    try:
                        pubcommands[cmd].do(args, connection, event)
                    except ArgsError:
                        connection.privmsg(
                            event.target, pubcommands[cmd].__doc__)
            else:
                print "User tried to perform " + cmd + ", but his/her power isnt high enough (" + str(stats["users"][speaker].power) + " vs " + str(pubcommands[cmd].powerreq) + ")"
                connection.privmsg(event.target, "Sorry, not enough power. (" + str(stats[
                                   "users"][speaker].power) + " vs " + str(pubcommands[cmd].powerreq) + ")")

        elif any(" ".join(msg).startswith(d) for d in ['hello', 'hi', 'howdy',
                                               "morning", "hey", "hola",
                                               "greetings", "top of the morning"]):
            connection.privmsg(event.target, "Hello to you " + speaker + "!")

        elif any(" ".join(msg).startswith(d) for d in ["thank you", "thanks", "ty", "arigato"]):
            connection.privmsg(event.target, "You are welcome smallsun")

        elif " ".join(msg).lower() in ["i hate you sungod!", "I hate sungod", "i love nekro", "i love nekromans", "xd", "nekro<3"]:
            stats["users"]["Frets"].sin += 1

        else:
            if stats["smart_mode"]:
                random.seed("".join(message.split(" ")[1:]))
            sungod_says(message, connection, event, speaker)
    elif connection_info["prefix"] in message.split(" ")[-1] and len(message.split(" ")[-1]) == len(connection_info["prefix"]):
        # TO-BE-DONE-LATER: ^ Needs a better implementation. "What is
        # happening, Sungod?" would send it as "What is happening," rather than
        # the inteded "What is happening?"
        s = " ".join(message.split(" ")[:-1])
        s = s.rstrip(",")
        if message[-1] in ["!", "?"]:
            s += message[-1]
        sungod_says(s, connection, event, speaker)
    else:
        pass

    stats["users"][speaker].previous_line = message
    global previous_line
    previous_line = message


def sungod_says(msg, connection, event, speaker):
    answer = "You make no sense"
    raw_str = msg.split(" ")

    if raw_str[0] == connection_info["prefix"]:
        raw_str = raw_str[1:]
    elif raw_str[0].startswith(connection_info["prefix"]) and raw_str[0][len(connection_info["prefix"])] in [".", ",", "?", "!"]:
        raw_str = raw_str[1:]
    if len(raw_str) == 0 or all([i == "" for i in raw_str]):  # TODO: Maybe find a better non hacky way for the message " "
        return
    raw_str = " ".join(raw_str)
    raw_str = raw_str.strip()
    print "raw_str: ", raw_str
    print "Raw string is: '" + raw_str + "'"

    if raw_str == "what is a man?":
        answer = "A miserable pile of secrets. But enough talk... Have at you!"
    elif raw_str == "what is w0bni doing?":
        answer = "Peeing or getting water."
    elif raw_str == "w0bni == good HoN player":
        answer = "Haha my son, good one."
    elif raw_str == "w0bni === good HoN player":
        answer = "Typesafely True"
    elif raw_str == "who is your favorite hero?" or raw_str == "who is your favourite hero?":
        answer = "All heroes are fine, but I find Jereziah to be an exceptionally bright believer. Furthermore, Martyr is a good guy too. Not to mention that w0bni!"
    elif re.search(r"[0-9]d[0-9]", raw_str):
        d = re.search(r"([0-9]+)d([0-9]+)", raw_str)
        dies, num = d.group(1), d.group(2)
        dies, num = int(dies), int(num)
        answer = 0
        for i in range(dies):
            answer += random.randint(1, num)
        answer = str(answer)
    elif re_scale.search(raw_str):
        r = re_scale.search(raw_str)
        grp = r.groupdict()
        print grp
        low = int(grp["low1"] or grp["low2"])  # if more groups, max()
        high = int(grp["high1"] or grp["high2"])
        print low, high
        print low < high
        if low < high:
            low, high = int(low), int(high)
            i = random.randrange(low, high+1)
            answer = "Hmm... About "+str(i)+"."
        else:
            answer = "I am uncertain"

    elif "note to" in raw_str:
        #----pffff bad code----
        # to = raw_str.split("note to ")[1].split(":")[0]
        # msg = raw_str.split(": ")[1]
        m = re_note.match(raw_str)
        if not m:
            return
        to, msg = m.groups()
        if to == "self":
            to = speaker
        bro = speaker
        stats["users"][to].checked_note = False
        print "#-----| THE USER HAS NO LONGER CHECKED NOTES"
        sendNote = urllib.urlopen("http://bbg.terminator.net/desknotes/newnote.php?to="+str(
            to)+"&from="+str(bro)+"&msg="+str(msg))
        resp = BeautifulSoup(sendNote)
        if "Error" in str(resp):
            answer = "Sorry, "+str(
                speaker)+", I could not note that. The bokk might be broken."
        elif "Success" in str(resp):
            answer = "I will make sure "+str(to)+" gets the message!"
        else:
            answer = "Nothing went wrong, yet something went wrong. The bokk is a mysterious item."

    elif " has commited a crime!" in raw_str:
        court(raw_str.split()[1], raw_str, event.target)
        return

    elif raw_str.startswith("how many"):
        n = random.randint(1, 4)
        if n == 1:
            i = random.randint(1, 20)
        elif n == 2:
            i = random.randint(20, 100)
        elif n == 3:
            i = random.randint(100, 1000)
        elif n == 4:
            i = random.randint(1000, 20000)
        answer = i

    elif " or " in raw_str:
        i = 0
        for word in raw_str:
            if word == "or":
                i += 1
            elif word.endswith(","):
                i += 1

        choices = [w for w in raw_str.split() if not w == "or"]
        if not len(choices) == 2:
            choices = choices[len(choices)-i-1:]
        for e, i in enumerate(choices):
            choices[e] = i.rstrip(",")

        choices[-1] = choices[-1].rstrip("?")

        print choices
        res = random.choice(choices)
        answer = "Hmmm... hard choice but I choose " + res

    elif "who " in raw_str.lower() or "who," in raw_str.lower():
        t = "who is" in raw_str.lower()  # The question is regarding a person
        if t:
            person = re.search("who is ([^?!\., ]+)", raw_str, re.IGNORECASE)
            if person:
                person = person.groups()[0]
                answers = [
                    " is a man of great reknown. The great warm book tells only good of him.", " is a blasphemous nekro", "... How I hate him... Please, don't speak of him",
                    " has done many a great deed! He is among the most fabolous and cute of my worshippers", " is an unknown name to me. Who is this?", " might not be the one you think he his, be careful.",
                    " is very infamous for his wicked brackets and semicolons, do not speak with him!"]
                answer = person + random.choice(answers)
            else:  # TODO: If no person is asked about!
                answer = random.choice(
                    ["I am not sure", "The bokk does not speak of him"])
        else:
            method = random.randint(1, 1)
            if method == 1:
                u = random.choice([u.capitalize() for u in
                                 stats["users"].keys()] + ["me"])
                if u == speaker.capitalize():
                    u = "you"
                answer = "That would be " + u

    elif any([i in raw_str.lower() for i in ["why ", "why,", " why?"]]):
        answers = [
            "Because I say so.", "It is written in the great warm bokk, therefore.", "It is undeniable",
            "for I made it so", "", "Are you sure it is so? So thats what happenend that night..."]
        methods = 8
        method = random.randint(1, methods)
        if method == 1 or method == 2:
            answer = random.choice(answers)
        elif method == 3:
            u = random.choice(stats["users"].keys()).capitalize()
            if u == speaker.capitalize():
                u = "yourself"
            prefix = random.choice(
                ["Maybe you should ask", "Ask", "Do not waste my time, ask",
                 "It would be wise to ask", "Warm book says you should ask"])
            suffix = random.choice(
                ["that question.", "yourself", "before I go mad and send you to nekromans or devell!"])
            answer = prefix + " " + u + " " + suffix
        elif method == 4:
            prefix = random.choice(["I hear", "I believe", "Check with",
                                   "It could be that", "According to the warm bokk,", "The fish say"])
            suffix = random.choice(
                ["has great knowledge regarding that", "is more than able to answer you that",
                 "is in possesion of the answer for that", "should have the answer"])
            u = random.choice(stats["users"].keys()).capitalize()
            while u == speaker.capitalize():
                u = random.choice(stats["users"].keys()).capitalize()
            answer = prefix + " " + u + " " + suffix
        elif method == 5:
            u = []
            if len(stats["users"].keys()) < 2:
                method = random.randint(1, methods)
            while len(u) < 2:
                i = random.choice(stats["users"].keys()).capitalize()
                if i not in u and i != speaker.lower():
                    u.append(i)
            answer = "You must walk to the " + \
                random.choice(
                    ["shapell", "shursh", "far away tribe", "bat cave", "place where the sun never sets",
                "fishes", "room of the great warm bokk", "place where the fishes live"]) +\
                ", " +\
                random.choice(
                    ["there you will find", "there you must search for", "and kill", ", and you must battle to death with",
                ", and you must dance with"]) +\
                " " + u[0] + " " +\
                random.choice(
                    ["under the tree", "inside the room with my symbol", "inside a box", "next to the great warm bokk",
                "in the water", "inside the secret room"]) +\
                ". He will guide you to " + u[
                    1] + " and he will have your answer."
        elif method in [6, 7, 8]:
            reason = random.choice(smart_memory["why"])
            answer = "That would be because " + reason

    elif "where " in raw_str.lower() or " where?" in raw_str.lower():
        t = False  # The type of question
        who = re.search(" where is .+", raw_str)
        if who:
            who = who.group(0)
            if who[-1] == "?":
                if who.split(" ")[-1][:-1].lower() in stats["users"].keys():
                    t = 1  # Where is the person?
                else:
                    t = 2  # Where is this (unknown) person or thing?
            # who = who.split(" ")[-1]
            elif who:
                t = 3  # Where is the person (doing/going/whatever)
            else:
                t = 4  # Where can I find

            if t == 1:
                method = random.randint(1, 2)
                if method == 1:
                    prefix = random.choice(
                        ["Last I checked, he was ", "I believe you will find him ", "Definitivly ",
                         "According to the light, he is "])
                    suffix = random.choice(
                        ["in the shapell", "outside", "reading in the great bokk, outside the shapell",
                         "softing with nekromans", "sleeping with the fishes", "adventuring"])
                    answer = prefix + "" + suffix
                elif method == 2:
                    u = random.choice(stats["users"].keys())
                    while u == speaker.capitalize() and u != who.capitalize():
                        u = random.choice(stats["users"].keys())
                    answer = "I believe " + u + " is softing with " + \
                        who + ", those scandalous dimmers"
            else:
                answer = "God knows."
        else:
            answer = random.choice(
                ["In the shapell", "With the bats", "Where the bats never leave",
                "Somewhere over the rainbow", "Not here atleast."])

    elif "when" == raw_str.lower().split(" ")[0]:
        answers = ["I would say about...",
            "Roughly", "As prophesied by the bokk,"]
        methods = 4
        method = random.randint(1, methods)
        if method == 1 or method == 2:
            prefix = random.choice(answers)
            answer = prefix + " " + str(random.randint(
                2, 59)) + random.choice([" minutes", " seconds"])
        elif method == 3:
            answer = "You must wait " + random.choice(["one", "two", "three",
                                                        "eight"]) + " " + random.choice(["days", "hours", "sunsets", "years"])
        elif method == 4:
            t = random.choice(
                ["The next time the sun sets", "When the bats cry", "When w0bni no longer leaks",
                             "When the fishes cry", "When the fish are thirsty", "When I am ready", "When the Baptists gather",
                             "When devell is dead", "When bats soft with fish", "When Baptist murders"])
            answer = "" + t

    elif "what" == raw_str.lower().split(" ")[0]:
        if re.search("should .* do", raw_str.lower()):
            if "doing" in raw_str.lower():
                answers = [
                    "Praying", "Bracing up", "Looking for the bat cave to hide in it",
                    "Running away", "Hiding", "Speaking with baptist", "Giving a gift to Baptist",
                    "Finding fish", "Fishing", "Sleeping with fishes", "Teaching"]
            else:
                answers = [
                    "Pray", "Brace yourself", "Look for the bat cave and hide in it",
                            "Run away", "Hide", "Speak with baptist", "Give a gift to Baptist",
                            "Sleep with the fishes", "Fight nekromans", "Find the meaning of fish",
                            "Fish", "Make like a fish, and bait"]
            answer = random.choice(answers)
        elif "will" in raw_str.lower():
            m = 1
            method = random.randint(1, m)
            if method == 1:
                answer = random.choice(
                    ["Many things can happen, if you pray you will be fine.",
                     "You will die.", "The fish will eat you.", "Nekromans will find you",
                                      "Shursh will be destroyed", ])
        elif raw_str.lower().split()[1] == "is":
            rest = " ".join(raw_str.lower().split()[2:])
            rest = rest.strip("?")
            suffix = random.choice(["unpredictable", "something I cannot tell",
                                    "something you must decide for yourself",
                                    "tons of ponies!",
                                    "harmless",
                                    "very dangerous, you should avoid it!",
                                    "unreachable", "something the great warm bokk tells a lot about. Read it and I am sure you will have your answer!",
                                    "untouchable like the fishes",
                                    "like sleeping with the fishes",
                                    "helping nekromans!",
                                    "very fun!",
                                    "the most important thing to do",
                                    "important",
                                    "like pie",
                                    "like awful cake!",
                                    "tasty",
                                    "hard work",
                                    "good for the fish",
                                    "unbelievable",
                                    "a secret",
                                    "the doing of nekromans",
                                    "the reason you are here!",
                                    "crucial for your mission",
                                    "bat",
                                    "uncontrollable",
                                    ])
            answer = rest + " is " + suffix
        else:
            answer = "SAVE YOURSELF FOR MARRIAGE!"

    elif raw_str.startswith("can you"):
        rest = " ".join(raw_str.lower().split()[2:])
        rest = rest.strip("?")
        rest = rest.replace("you", "I")
        rest = rest.replace("I", "you")
        rest = rest.replace("me", "you")
        rest = rest.replace("we", "you")
        rest = rest.replace("your", "my")
        rest = rest.replace("yours", "mine")

        rest = rest.replace("us", "you")

        method = random.randint(1, 2)

        if method == 1:
            answer = "I do not think I am able to " + rest + ", unfortunately"

        elif method == 2:
            answer = rest + "ing is an easy task for me! Ofcourse!"

#    elif "how" == raw_str.lower().split(" ")[1]:
#       answers =
    elif raw_str.endswith("?"):

        method = random.randint(1, 9)
        i = len(re.findall(r"\?", raw_str))
        answers = [
            "abseloteli", "deliberator", "no shancè", "as clair as my lihgt",
            "^sLook into the light, there you will find your answer.", "no",
            "undeniabeliterly", "When I burn out", "SLEEP WITH THE FISHES", "Could be", "Clearly"]
        subfix = " is the answer you seek"
        prefix = random.choice(["I believe ", "Hmmm... "])
        print "'''''IIIIIIII!!!'''''"
        print i
        if i > 2:
            prefix = "Patience, small son. "
            method = 1
        elif i == 2:
            subfix = ", in both your cases."
        midfix = random.choice(answers)

        if midfix.startswith("^s"):
            prefix = ""
            midfix = midfix[2:]
            method = 2
        if method == 1 or method == 2 or method == 11:
            answer = prefix + '"' + midfix + '"' + subfix
        elif method == 3 or method == 4:
            answer = "" + midfix.capitalize() + subfix
        elif method == 6 or method == 7:
            answer = "As said in the great warm bokk: " + \
                '"' + midfix + '"' + subfix
#        elif method == 8:
#            answer = "Did you know I am very far away from you?"
        elif method == 8 or method == 5:
            answer = "Is '" + midfix + "' the answer you seek, " + random.choice(
                ["by chance?", "perhaps?", "or is my wisdom unfilling?"])

    elif raw_str.endswith("!"):
        answers = [
            "Don't you dare!", "Who do you think you are, trying to command me like that?",
            "You filthy caveman, stop this or I will burn you to ashes"]
        method = random.randint(1, 3)
        if method == 1 or method == 2:
            answer = random.choice(answers)
        elif method == 3:
            answer = "You bet I will, " + speaker + "!"

    else:
        answer = "Not sure what you are saying, my son."

    if not answer:
        answer = "I do not have an answer, for some reason!"
    connection.privmsg(event.target, answer)


def court(speaker, message, chn):
    if speaker.lower() in [s.lower() for s in stats["users"].keys()]:
        faithful_cap = 0.06
        evil_cap = 0.04

        total_faith = sum([math.sqrt(f)
                          for f in [u.faith for u in stats["users"].values()]])
        speaker_faith = math.sqrt(stats["users"].get(speaker).faith)
        if math.sqrt(speaker_faith) > total_faith * faithful_cap:
            say("Oh no! How could someone as pure as " +
                speaker+" have commited such mischief?", chn)
        elif total_faith * faithful_cap > math.sqrt(speaker_faith) > total_faith * evil_cap:
            s = "I see. So this one is an impure one. I wonder why he has become like this."
            if random.randint(1, 2) == 1:
                influencer = random.choice([u.name for u in stats[
                                           "users"].values() if math.sqrt(u.faith) < total_faith * evil_cap])
                if influencer:
                    s = s + " Maybe it was the act of the foul " + \
                        influencer + "."
            say(s, chn)
        else:
            say("I knew " + speaker +
                " was up to no good! Please, let us settle this.", chn)

    else:
        say("Bring him here, now! And I shall pass my judgement.", chn)


#
# init stuff
#

def on_disconnected(socket):
    global server
    print "[WARNING] lost connection"
    server.connect(connection_info["network"], connection_info[
        "port"], connection_info["nick"], ircname=connection_info["name"])


def load_commands(cmd):
    """
    Takes a module/file/command and adds it to the respective dictionaries
    """

    commands = None
    while True:
        try:
            cmodule = __import__(cmd)
        except TypeError:
            print "Failed importing " + str(cmd) + ", possibly not a module."
        else:
            commands = cmodule.commands
            break

        try:
            commands = list(cmd)
        except TypeError:
            print "Failed making a list of " + str(cmd) + ", possibly not a list of commands."
        else:
            break  # dancing is cool. breakdancing.

    for c in commands:
        if c.type == "pub":
            global pubcommands
            if c.trigger in pubcommands:
                print "WARNING: A command with trigger '" + c.trigger + "' already exists. Ignoring."
            else:
                pubcommands[c.trigger] = c()


def load_hooks():
    import pkgutil
    import os
    import hooks
    for i in [name for _, name, _ in pkgutil.iter_modules(['hooks'])]:
        mod = __import__("hooks."+i, fromlist="hooks")
        for h in mod.hooks:
            Hooks.register_perma_hook(h)
    #===========================================================================
    # print dir(hooks)
    # hook_path = os.path.join(os.getcwd(),"hooks")
    # print hook_path
    # for i in [i for i in os.listdir(hook_path) if i.endswith(".py")]:
    #    module = __import__(os.path.join(hook_path,i))             HAHAHA MEGA COMMENT BLOCK
    #    if not "hooks" in dir(module):
    #        print "EXTENSION ERROR: The hook extension does not contain a hook dir"
    #    else:
    #        for h in module.hooks:
    #            Hooks.register_perma_hook(h)
    #=========================================================================


def save_settings(config="stats.db"):
    print "Trying to save"
    s = shelve.open(config)
    s.clear()
    s.update(stats)
    # for k,v in stats.items():
    #    if stats["debug"]:   print "k:%s, v%s"%(k,v)
    #    s[k] = v
    s.close()
    print "Succesfully saved"


def load_settings(config="stats.db"):
    global stats
    print "Trying to load"
    s = shelve.open(config)
    # print len(s.items() )
    # for k,v in s.items():
    #    stats[k] = v
    for c, u in stats["users"].items():
        new = User.update_user(u)
        stats["users"][c] = new
    if s:
        stats.update(dict(s.items()))
    s.close()
    print len(stats.items())
    print "Succesfully loaded!"


def save_error(error):
    """
    Todo: figuring out bloody file paths
    """
    f = open(os.path.join("debug", "crash.txt"), "w")
    f.write(str(error))
    pass


def auto_save():
    print "Auto: Saving"
    save_settings()
    delay = stats["autosave_interval"]
    if stats["arena_enabled"]:
        arena.save_heroes()
    # reddit.start()

    irc.execute_delayed(delay, auto_save)


def rss_check():
    for i in stats["rss"]["feeds"]:
        f = feedparser.parse(i)
        for e in f["entries"]:
            print time.strftime("%Y %m %d %H:%M:%S", e.updated_parsed) + " < " + time.strftime("%Y %m %d %H:%M:%S", stats["rss"]["last"]) + "?"
            if e.updated_parsed < stats["rss"]["last"]:
                print "BREAKING" + time.strftime("%Y %m %d %H:%M:%S", e.updated_parsed) + " < " + time.strftime("%Y %m %d %H:%M:%S", stats["rss"]["last"])
                break
            else:
                for s in [""+f.feed.title+": "+e.title] + html2text.html2text(e.summary).split("\n")[:8] + [e.link.strip("\n")]:
                    # print repr(s)
                    s = str(s.encode("iso8859_10", "ignore"))
                    server.privmsg(connection_info["channel"], s)
    stats["rss"]["last"] = time.gmtime()


def auto_rss_check():
    print "Auto: RSS check"
    rss_check()
    irc.execute_delayed(stats["rss"]["interval"], auto_rss_check)


def git_check():
    url = "https://github.com/Sebsebeleb/BadlybadSpace/commits/master.atom"
    tag = stats["git"].get("tag")
    if tag:
        f = feedparser.parse(url, etag=tag)
    else:
        f = feedparser.parse(url)

    stats["git"]["tag"] = f.etag

    for i in reversed(f.entries):
        url = PyNify.tinyfy(i.link)
        s = "'" + i.title + "' by " + i.author + " (" + url + ")"
        for chan in config.get("startup", "channels").split():
            server.privmsg(chan, s)


def auto_git_check():
    print "[GIT] Checking"
    git_check()
    irc.execute_delayed(stats["rss"]["interval"], auto_git_check)


def tell_pie_jokes():
    irc.execute_delayed(60*60*3, tell_pie_jokes)

    joke = random.choice(pie_jokes)
    for chan in config.get("startup", "channels").split():
        server.privmsg(chan, ""+joke[0])
        irc.execute_delayed(10, server.privmsg, (chan, ""+joke[1]))
        irc.execute_delayed(11, server.privmsg, (
            chan, "http://www.youtube.com/watch?v=_Rav9ijyyZk"))


def initiate_irc():
    # Create an IRC object

    # irclib.DEBUG = True

    # Create a server object, connect and join the channel
    global server, connection_info, stats, irc
    irc = irclib.IRC(on_disconnect=on_disconnected)
    server = irc.server()
    server.connect(connection_info["network"], connection_info[
        "port"], connection_info["nick"], ircname=connection_info["name"])
    for chan in config.get("startup", "channels").split():
        server.join(chan)

    connection_info["server"] = server

    irc.add_global_handler('privmsg', handlePrivMessage)
    irc.add_global_handler('pubmsg', handlePubMessage)
    irc.add_global_handler('join', handleJoin)

    print stats["autosave_interval"]
    irc.execute_delayed(stats["autosave_interval"], auto_save)
    # irc.execute_delayed(60*20,tell_pie_jokes)
    # rss_check()
    # irc.execute_delayed(stats["rss"]["interval"],auto_rss_check)
    irc.execute_delayed(stats["rss"]["interval"], auto_git_check)

    print connection_info["nickservpass"]
    server.privmsg("nickserv", connection_info["nickservpass"])
    print "Server is:", server
    if stats["arena_enabled"]:
        arena.init(server)

    # Jump into an infinite loop

    while True:
        try:
            irc.process_forever()
        except Exception as e:

            stats["error"] = e.message
            if stats["immortal"] == True:
                # server.privmsg(connection_info["channel"], "YOU CANNOT KILL
                # ME, FOOL. I AM IMMORTAL HAHAHA!")
                print "----Error occured----"
                print traceback.format_exc()
                print "---------------------"
            else:
                save_error(e)
                # save_settings()
                raise


def initiate_cli():
    def f():
        i = raw_input("q to quit> ")
        if i == "q":
            pass
        else:
            exec i in globals(), locals()
            f()
    t = threading.Thread(target=f)
    t.start()


if __name__ == "__main__":

    # load_hooks()
    load_commands(builtincmds)
    try:
        load_settings()
    except Exception as e:
        print "Loading settings failed; ", e
        raise
    # initiate_cli()
    initiate_irc()
    save_settings()

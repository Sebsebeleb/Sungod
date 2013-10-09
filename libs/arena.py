import random
import time
import shelve
import math
import os

"""
IRC codes:
 bold
4 hp red text
5 brown - Strength
11 dexterity

"""

channel = "#sunfields"

levels = [2,3,5,15,19,25,34,70,95,106,135,150,200,300,400,1000,100000]

heroes = {}
traits = ["spiky","cunning","burly","strong","ablaze","skilled","smart","barraging",
          "accurate", "daredevil", "bottomless", "undying","quick to learn",
          "drunk", "glass cannon"]

patch_notes = ["Sunfields 1.87",
               "- A new spell!",
               ]
class Event():
    def __init__(self, damage, action, events=None):
        self.damage = damage
        self.action = action
        self.events = events
        
class Hero:
    def __init__(self, owner, name, pre_traits = None):
        if pre_traits == None:
            self.traits = random.sample(traits,2)
        else:
            self.traits = (pre_traits + random.sample(traits,2))[:2]
        self.name = name
        self.owner = owner
        self.base_str = self.base_dex = self.base_int = self.base_end = 3
        self.extra_str = self.extra_dex = self.extra_end = self.extra_int = 0
        
        self.level = 1
        self.xp = 0
        self.rank_points = 0
        
        self.stat_points = 5
        self.skill_points = 1
        if "quick to learn" in self.traits:
            self.skill_points += 1
        
        self.wins = 0
        self.losses = 0
        
        if "strong" in self.traits:
            self.base_str += 3
        if "skilled" in self.traits:
            self.stat_points += 2
        if "drunk" in self.traits:
            self.base_int -= 2
            self.base_str += 7
            self.base_dex -= 2
            self.base_end += 4
        if "glass cannon" in self.traits:
            self.base_end -= 2
            self.base_str -= 2
            self.base_int += 7
        
        self.spells = []
        self.states = []
        
        if name.lower() == "chuck norris":
            self.base_str = 89
            self.base_end = 67
            self.base_dex = 29
            self.base_end = 20
            
        global heroes
        heroes[owner] = self
        
    @property
    def win_percent(self):
        if self.wins == 0 and self.losses == 0:
            return "unranked"
        elif self.losses == 0:
            return "100%"
        elif self.wins == 0:
            return "0%"
        else:
            return str(round(float(self.wins)/float(self.wins+self.losses),2)*100)+"%"
    @property
    def dexterity(self):
        return self.base_dex + self.extra_dex
    @property
    def strength(self):
        return self.base_str + self.extra_str
    @property
    def intelligence(self):
        return self.base_int + self.extra_int
    @property
    def endurance(self):
        return self.base_end + self.extra_end
    @property
    def mana_regen(self):
        return 0.25
        
    def clean_up(self,enemy):
        for i in self.spells:
            i.cd_counter = i.cd_begin
        self.extra_end = self.extra_str = self.extra_int = self.extra_dex
        for s in self.states:
            s.on_decay(enemy)
        self.states = []     
          
    def on_turn(self,enemy):
        self.mana += self.mana_regen
        if "bottomless" in self.traits:
            self.mana += 0.5
        if "undying" in self.traits:
            self.hp += 1
        for s in self.states:
            print "THIS IS STATE: ", s
            s.update(enemy)
        for i in self.spells:
            d = 1
            if "barraging" in self.traits:
                d +=1
            i.cd_counter -= d
        self.mana = min(self.get_maxMP(),self.mana)
        self.hp = min(self.get_maxHP(),self.hp)
            
    def action(self,enemy):
        """
        Decides what action to take
        """
        for i in self.spells:
            print i.cd_counter, i, i.owner.name
            if i.can_cast(enemy):
                return i.cast(enemy)
                break
        else:
            print "Couldnt cast any spells, attacking!"
            return self.damage(enemy)

    def damage(self,enemy):
        miss_chance = 0.13 - self.dexterity
        if "drunk" in self.traits:
            miss_chance = 0.33
        if "accurate" in self.traits:
            miss_chance -= 0.25
        if random.random() < miss_chance:
            return Event(-2,"tries to attack but misses!")
        dam_type = "damages"
        print self.strength
        low = self.strength * 1.5 + self.dexterity * 0.5
        high = self.strength * 1.5 + self.dexterity *1.5
        if "daredevil" in self.traits:
            high += self.dexterity * 1.5
        print low, high
        damage = random.randint(max(int(low),0), max(int(high),0))
        print "low: ", low, " high: ", high
        crit_chance = 0.05 + self.dexterity * 0.015
        if "cunning" in self.traits:
            crit_chance += 0.15
        if random.random() < 0.05 + self.dexterity * 0.015:
            if "spiky" in self.traits:
                damage = damage *3
            else:
                damage = damage * 2
            dam_type = "CRITS"
        return Event(damage,dam_type)
    
    def on_damage(self,enemy,damage):
        for s in self.states:
            s.on_damage(enemy,damage)
            
    def on_damaged(self,enemy,damage):
        print "yes hello, this is on_damaged speaking?"
        print len(self.states)
        for s in self.states:
            print "This is ", s
            s.on_damaged(enemy,damage)
    
    def get_maxHP(self):
        hp = 35+self.endurance* 8 + self.strength*2
        if "burly" in self.traits:
            hp += 20
        if "daredevil" in self.traits:
            hp -= 20
        if "glass cannon" in self.traits:
            hp -= 20
        return hp
    
    def get_maxMP(self):
        mana = 10+self.base_int*3
        if "smart" in self.traits:
            mana += 15
        return mana
    
    def repr_stats(self, connection):
        for i in ["The " + self.traits[0] + " and " + self.traits[1] + " " + self.name,
                  "unallocated stat points, skillpoints:" + str(self.stat_points) + ", " + str(self.skill_points),
                  "wins/losses: " + str(self.wins) +"/"+str(self.losses) + " " + self.win_percent,
                  "level, xp: " + str(self.level)+", 6"+ str(self.xp) + "1/6" + str(levels[self.level]),
                  "rank points: 11" + str(self.rank_points),
                  "owner: " + str(self.owner),
                  "str/dex/end/int: 5%s1/11%s1/3%s1/12%s"%(self.base_str,self.base_dex,self.base_end,self.base_int),
                  ]:
            connection.privmsg("#sunfields",i)
    def learn(self,spell):
        print "Trying to learn",spell
        if self.skill_points > 0:
            if learnable_skills.has_key(spell):
                self.spells.append(learnable_skills[spell](self))
                self.skill_points -= 1
                print "Learned ",spell,"!"
    def apply_state(self,state):
        self.states.append(state)
        
    def has_state(self,state_name):
        n = len([s for s in self.states if s.name == state_name])
        if n:
            return n
        else:
            return False

class State():
    duration = 0
    dur_left = duration
    name = "Stateless State"
    def __init__(self,owner,enemy):
        self.name = self.name
        self.owner = owner
        self.dur_left = self.duration
        self.on_apply(enemy)
    def update(self,enemy):
        if self.dur_left < 0:
            self.on_decay(enemy)
            self.owner.states.remove(self)
            return
        self.dur_left -= 1
        print self
        self.on_update(enemy)
    def on_apply(self,enemy):
        pass
    def on_decay(self,enemy):
        pass
    def on_update(self,enemy):
        pass
    def on_damaged(self,enemy,damage_dealt):
        pass
    def on_damage(self,enemy,damage_dealt):
        pass
    
class Overpower_State(State):
    duration = 1
    name = "Overpower"
    def on_apply(self,enemy):
        print self.owner.name
        self.owner.extra_str += 10
        self.owner.extra_dex += 5
    def on_decay(self,enemy):
        self.owner.extra_str -= 10
        self.owner.extra_dex -= 5
        
class Rejuvenation_State(State):
    duration = 4
    name = "Rejuvenation"
    def on_apply(self,enemy):
        self.owner.extra_end += 4
    
    def on_update(self,enemy):
        self.owner.hp += self.owner.intelligence
    
    def on_decay(self,enemy):
        self.owner.extra_end -= 4
        
class EternalFire_State(State):
    name = "Eternal Fire"
    duration = 4
    def on_update(self,enemy):
        self.owner.hp -= 7
        
class Thorns_State(State):
    name = "Thorns"
    duration = 3
    def on_damaged(self,enemy,damage_dealt):
        enemy.hp -= int(damage_dealt / 3.0)
    
class ManaShield_State(State):
    name = "Mana Shield"
    duration = 50
    def on_damaged(self,enemy,damage_dealt):
        mana_spent = min(self.owner.mana,damage_dealt/4.0)
        self.owner.mana -= mana_spent
        self.owner.hp += mana_spent*4

class CurseOfImpendingDeath_State(State):
    name = "Curse of Death stack"
    duration = 9001
    
class Spell():

    mana_cost = 0
    cooldown = 1
    cd_counter = cooldown
    cd_begin = cooldown
    def __init__(self,owner):
        self.owner = owner
        self.cd_counter = self.cd_begin
    def cast(self,enemy):
        pass
    def effect(self):
        pass
    def can_cast(self,enemy):
        """
        if it can cast, will return True and do all mana cost stuff
        """
        if self.cd_counter > 0:
            print "cooldown: ", self.cd_counter
            return False
        if self.mana_cost > self.owner.mana:
            print "not enough mana: ",self.mana_cost, " vs owners ",self.owner.mana
            return False
        else:
            if self.will_cast(enemy):
                self.owner.mana -= self.mana_cost
                self.cd_counter = self.cooldown
                return True
            else:
                return False
    def will_cast(self,enemy):
        return True

class Healing(Spell):
    """
Uses the spirit of Sungod to bathe yourself in a healing light!
Heals 15+int*4 to 20+int*6 health"""
    mana_cost = 6
    cooldown = 3
    cd_counter = cooldown
    def cast(self,enemy):
        i = self.owner.intelligence
        heal_amount = random.randint(int(12+i*3.5), int(18+i*5))
        self.owner.hp += heal_amount
        return Event(-1,"8Healing1, healing himself for 4"+str(heal_amount)+"4 hp!")
    def will_cast(self,enemy):
        if self.owner.get_maxHP() - self.owner.hp < 20+self.owner.intelligence*6 - 15:
            return False
        else:
            return True
    
class Rejuvenation(Spell):
    """Watch out, it's getting HoT in here!"""
    
    mana_cost = 8
    cooldown = 6
    cd_begin = 2
    def cast(self,enemy):
        self.owner.apply_state(Rejuvenation_State(self.owner,enemy))
        return Event(-1, "3Rejuvenation1, giving him some endurance and healing him every turn")
    
    def will_cast(self,enemy):
        if self.owner.get_maxHP() - self.owner.hp  < self.owner.intelligence * 2:
            return False
        else:
            return True
    
class EternalFire(Spell):
    """Watch out, it's getting DoT in here!"""
    mana_cost = 10
    cooldown = 5
    cd_begin = 1
    def cast(self,enemy):
        enemy.apply_state(EternalFire_State(enemy,enemy))
        return Event(-1, "5Eternal Fire1, burning his enemy!")
        
        
class Fireball(Spell):
    """
Throws a mighty fireball towards your enemy, dealing huge damage!
Deals 8+int*3 to 14+int*4 damage"""

    mana_cost = 6
    cooldown = 3
    cd_counter = cooldown
    def cast(self,enemy):
        return Event(self.damage(),"casts a 7Fireball1 at")
    def damage(self):
        i = self.owner.intelligence
        damage = random.randint(8+int(i*3),14+i*4)
        if "ablaze" in self.owner.traits:
            damage += 10
        return damage
    
class CatsGrace(Spell):
    """
You are so agile you are extremely agile!
Gives you 1+int/8 to 2+int/3 dex for the rest of the fight"""

    cooldown = 3
    mana_cost = 6
    def cast(self,enemy):
        i = self.owner.intelligence
        dx = random.randint(1+i/8,2+i/3)
        self.owner.extra_dex += dx
        return Event(-1, "10Cat's Grace1, increasing his dexterity by "+str(dx)+"!")
    
class Overpower(Spell):
    """
RAAAWR! You use the spirit of Sungod to grant yourself strength!
Grants 10 strength and 5 dexterity for one round"""

    cooldown = 4
    mana_cost = 4
    def cast(self,enemy):
        self.owner.apply_state(Overpower_State(self.owner,enemy))
        return Event(-1,"14Overpower1, making his/her next attack mighty frightening!")
    
class Thorns(Spell):
    """
Touch me, I wanna feel your damage!
Returns damage to the enemy when you are damaged."""
    cooldown = 7
    cd_begin = 1
    duration = 4
    mana_cost = 14
    def cast(self,enemy):
        self.owner.apply_state(Thorns_State(self.owner,enemy))
        return Event(-1,"3Thorns1, making the enemy take damage when they hit him!")
    
class ManaShield(Spell):
    """ahue"""
    cooldown = 9001
    cd_begin = 0
    mana_cost = 6
    def cast(self,enemy):
        self.owner.apply_state(ManaShield_State(self.owner,enemy))
        return Event(-1,"2Mana Shield1 to use his mana to protect his vitality")
    
class ManaDrain(Spell):
    """mmmm yummy!"""
    cooldown = 5
    cd_begin = 3
    mana_cost = 7
    def cast(self,enemy):
        i = self.owner.intelligence
        mana_drained = 12 + i/2
        m = min(enemy.mana,mana_drained)
        self.owner.mana += m
        enemy.mana -= m
        enemy.hp -= int(m/2)
        return Event(-1,"2Mana Drain1, draining 2"+str(m)+"1 mana, and dealing 10"+str(int(m/2.0))+"1 to his opponent!")
    
    def will_cast(self,enemy):
        i = self.owner.intelligence
        if self.owner.mana + 6 + i/4 < self.owner.get_maxMP() and enemy.mana > 7:
            return True
        else:
            return False

class CurseOfImpendingDeath(Spell):
    """Kill your enemy! Slooowly!"""
    cooldown = 3
    mana_cost = 5
    def cast(self,enemy):
        enemy.apply_state(CurseOfImpendingDeath_State(self.owner,enemy))
        stacks = enemy.has_state("Curse of Death stack")
        damage = 10 + stacks * int((3 + self.owner.intelligence/3))
        return Event(damage, "2 Impending Death, the clock ticks, tick tock... ")
    
class LifeDrain(Spell):
    """Mmmm, tasty!"""
    cooldown = 4
    mana_cost = 7
    def cast(self,enemy):
        damage = 10 + self.owner.intelligence * 3
        self.owner.hp += damage
        return Event(damage, "2 Life Drain, draining %s health for himself!"%(damage))
    
    
def update_stats(winner, loser, connection):
    winner.wins += 1
    loser.losses += 1
    highest = max(winner.level,loser.level)
    lowest = max(winner.level,loser.level)
    rank_dif = winner.rank_points - abs(winner.rank_points - loser.rank_points)
    #xp = max(int((min(5,1+(highest-lowest/highest)) * rank_dif / 100.0)),0)
    rank_points = min(5,(winner.rank_points - loser.rank_points)/4+5) #temp calculation
    xp = loser.level
    winner.xp += xp
    loser.xp += xp/5
    winner.rank_points += rank_points
    loser.rank_points -= rank_points
    if winner.level < len(levels):
        if winner.xp > levels[winner.level]:
            winner.level += 1
            winner.stat_points += 1
            winner.xp = 0
            winner.skill_points += 1
            
            combat.log.append([winner.name + " has leveled up!",winner.name + " is now level " + str(winner.level)])
    return rank_points, xp
    
def _get_hero(owner):
    try:
        return heroes[owner]
    except:
        repr(heroes)
    
def add_log(message):
    global log
    if isinstance(message,list):
        log.append(message)
    else:
        log.append([message])


class Combat():
    def __init__(self, users, connection, auto=True):
        self.turn = 1
        
        self.team1 = users[0]
        self.team2 = users[1]
        
        self.users = zip(users[0],users[1])
        
        for u in users:
            u.hp = u.get_maxHP()
            u.mana = u.get_maxMP()
            
        self.attack = False
        self.l = []
        self.log = []
        a_action = None
        b_action = None
        if auto:
            winner = None
            while not winner:
                self.fight_turn()
                if all(hp < 0 for hp in self.team2):
                    winner = self.defender
                    loser = self.attacker
                elif all(hp < 0 for hp in self.team1):
                    winner = self.attacker
                    loser = self.defender
                else:
                    winner = "???"
                    print "Something terribly wrong here"
        else:
            global active_combat
            active_combat = self

        self.attacker.clean_up(self.defender)
        self.defender.clean_up(self.attacker)
        rank,xp = update_stats(winner,loser,connection)
        self.log.append(["AND THE WINNER IS... " + winner.name + "! Winning him/her an amazing 11" + str(rank) + "1 ranking and 6" + str(xp) + "1 xp!"])
        self.log_summarize(connection)
        
        
        
    def fight_turn(self):#, a_action, d_action):@TODO: Implement  
        if not self.attack: 
            self.l.append("TURN "+str(self.turn)+"!")
        if self.attack:
            event = self.attacker.action(self.defender)
            self.defender.hp -= max(event.damage,0)
            self.attacker.on_turn(self.defender)
            if event.damage > 0:
                self.l.append("%s %s %s for 10%s1 damage!"%(self.attacker.name,
                                    event.action,
                                    self.defender.name,
                                    event.damage))
                self.attacker.on_damage(self.defender,event.damage)
                self.defender.on_damaged(self.attacker,event.damage)

            elif event.damage == -1:
				self.l.append("%s uses %s"%(self.attacker.name,event.action))
            elif event.damage == -2:
				self.l.append("%s %s"%(self.attacker.name,
									event.action))
        else:
            event = self.defender.action(self.attacker)
            self.attacker.hp -= event.damage
            self.defender.on_turn(self.attacker)
            if event.damage > 0:
				self.l.append("%s %s %s for 10%s1 damage!"%(self.defender.name,
									event.action,
									self.attacker.name,
									event.damage))
				self.attacker.on_damaged(self.defender,event.damage)
				self.defender.on_damage(self.attacker,event.damage) 

            elif event.damage == -1:
				self.l.append("%s uses %s"%(self.defender.name,
									event.action
									))
            elif event.damage == -2:
				self.l.append("%s %s"%(self.defender.name,
									event.action))
                                    
        if self.attack: 
			self.turn +=1
        self.l.append(self.log_status(self.attacker, self.defender))
        self.log.append(self.l)
        self.l = []
        self.attack = not self.attack
        
    def log_status(self, attacker, defender):
        s1 = "%s hp: 4%s1/4%s1 mp: 2%s1/2%s1 "%(attacker.name, attacker.hp,attacker.get_maxHP(),int(attacker.mana),attacker.get_maxMP())
        s1 = s1.ljust(20)
        mid = " vs " 
        s2 = "%s hp: 4%s1/4%s1 mp: 2%s1/2%s1 "%(defender.name,defender.hp,defender.get_maxHP(),int(defender.mana),defender.get_maxMP())
        s2 = s2.rjust(20)
        return s1 + mid + s2
            
    def log_summarize(self,connection):
        sleep = 0
        sleep_interval = 2
        for i in self.log[-50:]:
            for l in i:
                connection.privmsg("#sunfields",l)
            time.sleep(2)
        self.log = []
    
def create_hero(owner, name,trts=None):
    if trts:
        Hero(owner,name,trts)
    else:
        Hero(owner,name,trts)
    
def spend_point(hero, stat,i):
    if i <= hero.stat_points:
        if stat == "str" or stat == "strength":
            hero.stat_points -= i
            hero.base_str += i
        elif stat == "int" or stat == "intelligence":
            hero.stat_points -= i
            hero.base_int += i
        elif stat == "dex" or stat == "dexterity":
            hero.stat_points -= i
            hero.base_dex += i
        elif stat == "end" or stat == "endurance":
            hero.stat_points -= i
            hero.base_end += i
        
    


def on_msg(connection,event):
    cmds = {
        "create":create_hero,
            }

    if event.target() != channel:
        return

    speaker = event.source().split('!') [0]
    msg = event.arguments()[0]
    print "Sunfield>" + speaker +": " + msg
    print "Sunfield cmd: "+msg
    cmd = msg.split()
    command,args = cmd[0],cmd[1:]
    print "Command: ", command, "Args: ", args
    
    if speaker in combat.users:
        if combat.valid_command(user, cmd):
            combat.user_do(user, cmd)
            return

    if command == "fight" or command == "c":
        global heroes
        print heroes
        a = " ".join(args)
        if not args:
            pass
        elif a == speaker:
            pass
        elif a not in heroes.keys():
            pass
        else:
            Combat(_get_hero(speaker),_get_hero(a),connection)
    elif command == "create" or command == "c":
        a = " ".join(args)
        name,waste,trts = a.partition(",")
        if trts:
            trts = [t.strip(" ") for t in trts.split(",")]
        if a == "":
            pass
        else:
            if trts:
                create_hero(speaker,name,trts)
            else:
                create_hero(speaker,name)
    elif command == "spend":
        i = 1
        if len(args) == 3 and args[1] == "*":
            i = int(args[2])
        spend_point(_get_hero(speaker),args[0],i)
    elif command == "stats":
        if not len(args) or args[0] == "":
            hero = _get_hero(speaker)
        elif heroes.has_key(args[0]):
            hero = _get_hero(args[0])
        else:
            hero = None
        if hero:
            hero.repr_stats(connection)
    elif command == "wipeYESIAMSURE":
		heroes = {}
		create_Sungod()
		create_dummy_hero("Dummy Weak",end=5)
		create_dummy_hero("Dummy Strong",end=10)
    elif command == "rename":
        if not len(args):
            pass
        else:
            heroes[speaker].name = " ".join(args)
    elif command == "save":
        save_heroes()
    elif command == "learn":
        _get_hero(speaker).learn(" ".join(args))
    elif command == "skills":
        connection.privmsg("#sunfields", ", ".join(learnable_skills.keys()))
    elif command == "traits":
        for i in traits:
            connection.privmsg("#sunfields",i)
    elif command == "retrain":
        print "-----retrain-----"
        print " ".join(args).split(",")
        t = [i for i in (" ".join(args)).split(",") if i != " "]
        print t
        new_traits = [t.strip(" ") for t in (" ".join(args)).split(",") if t != " "][:2]
        print new_traits
        print len(new_traits)
        if len(traits) == 1:
            new_traits.append(random.choice([i for i in traits if i != new_traits[0]]))
        elif len(traits) == 0:
            new_traits = random.sample(traits,2)
        h = _get_hero(speaker)
        print h.traits
        h.traits = new_traits
        print h.traits
             
    elif command == "patch":
        display_patch(connection)
    elif command == "info":
        a = " ".join(args)
        if learnable_skills.has_key(a):
            connection.privmsg("%sunfields","skill: "+a)
            for h in learnable_skills[a].__doc__.split("\n"):
                connection.privmsg("#sunfields",h)
    elif command == "heroes":
        for i in heroes.values():
            connection.privmsg("#sunfields",i.name+" ("+i.owner+")")
    if hasattr(cmds,command):
        #doesnt seem to work
        print "oh my! cmd!"
        cmds[command](*args)
    else:
        print "no have!"
        
def save_heroes(config = "stats\\heroes.db"):
    s = shelve.open(config)
    for k,v in heroes.items():
        s[k] = v
    
def load_heroes(config = "stats\\heroes.db"):
    global heroes
    print os.path.abspath(os.path.curdir)
    print os.path.abspath(config)
    try:
        s = shelve.open(config)
    except Exception:
        f = open(config, "wb")
        f.close()
        s = shelve.open(config)
        
    for k,v in s.items():
        print k,":",v
        heroes[k] = v
        
def create_Sungod():
        h = Hero("Sungod","Sungod")
        h.level = 15
        h.stat_points += 14
        h.skill_points = len(learnable_skills.keys())+1
        for i in range(h.stat_points):
            i = random.randint(1,4)
            if i == 1:
                h.base_str += 1
            elif i == 2:
                h.base_dex += 1
            elif i == 3:
                h.base_int += 1
            elif i == 4:
                h.base_end += 1
        h.stat_points = 0
        for s in random.sample(learnable_skills.keys(),6):
            h.learn(s)
            
def create_dummy_hero(name,end=5):
    h = Hero(name,name)
    h.base_dex = 0
    h.base_end = end
    h.base_int = 5
    h.base_str = 0
    h.learn("Thorns")
    h.skill_points = 0
    h.stat_points = 0


def display_patch(connection):
    for i in patch_notes:
        connection.privmsg("#sunfields",i)


def init(heroes_dict):
    # heroes = heroes_dict
    load_heroes()
    print "HEROES: ", heroes
    if not heroes.has_key("Sungod"):
        create_Sungod()
    if not heroes.has_key("Dummy"):
        create_dummy_hero("Dummy Weak",end=5)
        create_dummy_hero("Dummy Strong",end=10)
    
learnable_skills = {"Fireball":Fireball,"Healing":Healing,"Cat's Grace":CatsGrace,
                    "Overpower":Overpower,"Eternal Fire":EternalFire,"Rejuvenation":Rejuvenation,"Thorns":Thorns,"Life Drain":LifeDrain,
                    "Mana Shield":ManaShield,"Mana Drain":ManaDrain,"Curse Of Impending Death":CurseOfImpendingDeath}

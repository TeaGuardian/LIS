import requests.exceptions
from data import token, my_token
from lis import Morpher, distance, limited_text_split
from datetime import datetime, timedelta
from random import randint
import os
import vk_api
import sys
from vk_api.longpoll import VkLongPoll, VkEventType
ENC, RUN, ADMIN, RETR = 'utf-8', True, 654275850, 0
FACAPS = [572255311, 654275850]
BlackList, GrayList, Users, Banned = [], [], {}, {}
mor = Morpher()


def is_banned(us_id):
    if str(us_id) not in Banned.keys():
        return False
    time = Banned[str(us_id)]
    if (datetime.now() - time) > timedelta(minutes=20):
        Banned.pop(str(us_id))
        return False
    return True


def ban(us_id):
    if str(us_id) not in Banned.keys():
        Banned[str(us_id)] = datetime.now()
    time = Banned[str(us_id)]
    if (datetime.now() - time) > timedelta(minutes=1):
        Banned[str(us_id)] = datetime.now()


class Timer:
    def __init__(self, tick):
        self.tick, self.last = tick, datetime.now()

    def tk(self):
        if (datetime.now() - self.last) > timedelta(seconds=self.tick):
            self.last = datetime.now()
            return True
        return False


def try_open(file):
    """проверка файла настроек на доступность"""
    try:
        f = open(file)
        f.close()
        return True
    except FileNotFoundError:
        return False


class User_session:
    def __init__(self, user_id, message, sender):
        self.id, self.last_active, self.last_message = user_id, datetime.now(), message
        self.sender, self.help, self.counter_ban, self.active_ban = sender, {}, 0, datetime.now()
        self.set_pach, self.poj, self.new = f"users/{self.id}.data", "==", True
        user_get = sender.users.get(user_ids=(user_id))[0]
        name = "traveler" if 'first_name' not in user_get.keys() else user_get['first_name']
        self.data = {'notify': "False", 'local_name': name}
        self.data_re = {'notify': lambda gr: gr in ["True", "False"], 'local_name': lambda gr: True}
        if os.path.exists(self.set_pach):
            self.new = False
            self.import_set()

    def import_set(self):
        self.procreate(self.set_pach)
        with open(file=self.set_pach, mode="r+", encoding=ENC) as file:
            for i in file.readlines():
                i = i.rstrip("\n")
                arg, rez = i.split(self.poj)
                self.data[arg] = rez

    def save(self):
        with open(file=self.set_pach, mode="w+", encoding=ENC) as file:
            rez = list(map(lambda i: f"{i}{self.poj}{self.data[i]}", self.data.keys()))
            file.write("\n".join(rez))

    def save_list(self, patch, lis):
        with open(file=patch, mode='w+', encoding=ENC) as file:
            file.write("\n".join(lis))

    def try_init(self) -> bool:
        si = "<LIS bot interface>\n"
        if is_banned(self.id):
            return False
        BlackList.extend(filter(lambda i: i not in BlackList, self.deparse("settings/blacklist.txt")))
        GrayList.extend(filter(lambda i: i not in GrayList, self.deparse("settings/graylist.txt")))
        for na, va in map(lambda g: g.split(self.poj), self.deparse("settings/helplist.txt")):
            self.help[na] = "\n".join(va.split("\\n"))
        if str(self.id) in BlackList:
            return False
        if str(self.id) in GrayList:
            if self.last_message == "on":
                mes = si + "The bot functions are available to you again.\nThank you, for choosing us"
                self.sender.messages.send(user_id=self.id, message=mes, random_id=randint(1, 200000))
                GrayList.pop(GrayList.index(str(self.id)))
                self.save_list("settings/graylist.txt", GrayList)
            else:
                return False
        mes = si + f"Hi, {self.data['local_name']}!✨\nYou are not marked as an exception, send 'off' to close the connection or 'help' to learn more."
        self.sender.messages.send(user_id=self.id, message=mes, random_id=randint(1, 200000))
        return True

    def procreate(self, patch):
        if not try_open(patch):
            with open(file=patch, mode='w+', encoding=ENC) as fi:
                pass

    def deparse(self, patch):
        self.procreate(patch)
        with open(file=patch, mode='r+', encoding=ENC) as file:
            rez = list(map(lambda i: i.rstrip("\n"), file.readlines()))
        return rez

    def command_selector(self, command):
        si = "<LIS bot interface>\n"
        fl, self.last_active = is_banned(self.id), datetime.now()
        tf = (datetime.now() - self.active_ban) > timedelta(minutes=1)
        if not fl:
            if self.counter_ban == 0 or self.counter_ban < 1:
                self.active_ban, self.counter_ban = datetime.now(), 1
            elif self.counter_ban > 0 and not tf:
                self.counter_ban += 1
            if tf:
                self.counter_ban = 0
            if self.counter_ban > 10:
                ban(self.id)
                self.counter_ban = 0
                self.sender.messages.send(user_id=self.id, message=si + "you are banned for 20 minutes",
                                          random_id=randint(1, 200000))
        if ("help" in command or "info" == command or "list" in command) and not fl:
            self.help_command(command)
        elif "off" == command:
            self.sender.messages.send(user_id=self.id, message=si + "goodbye traveler!", random_id=randint(1, 200000))
            GrayList.append(str(self.id))
            self.save_list("settings/graylist.txt", GrayList)
            Users.pop(str(self.id))
        elif "switch yandex " in command and not fl:
            user = YandexTestTask(self.id, command, self.sender, command.lstrip("switch yandex "))
            if user.try_init():
                Users[str(self.id)] = user
        elif "set user." in command and not fl:
            self.sender.messages.send(user_id=self.id, message=si + self.user_set_com(command), random_id=randint(1, 200000))
        elif "get user." in command and not fl:
            self.sender.messages.send(user_id=self.id, message=si + self.user_get_com(command), random_id=randint(1, 200000))
        elif "set phrase" in command and not fl:
            self.add_phrase(command.lstrip("set phrase "))
        elif "get database" in command and not fl:
            self.sender.messages.send(user_id=self.id, message=si + self.get_all_data(), random_id=randint(1, 200000))
        elif "delete phrase" in command and not fl:
            self.sender.messages.send(user_id=self.id, message=si + self.delite_phrase(command.lstrip("delete phrase ")), random_id=randint(1, 200000))
        elif "check phrase" in command and not fl:
            self.sender.messages.send(user_id=self.id, message=si + self.get_phrase(command.lstrip("check phrase ")), random_id=randint(1, 200000))

    def user_set_com(self, command):
        ccd, rez = command.split("."), ""
        if len(ccd) != 2 or len(ccd[1].split()) != 2:
            return "error: invalid command length; try [set help]"
        par, val = ccd[1].split()
        cn = par in self.data_re.keys()
        cl = self.data_re[par](val) if cn else False
        if "sudo set user" == ccd[0]:
            if cn and not cl:
                return f"error: wrong type of argument; try [{ccd[0]}.{par} list]"
            rez = "success by sudo" if not cn else "success"
        else:
            if not cn:
                return f"wrong value; no match for [{par}]; try [set list] or [sudo {command}]"
            if not cl:
                return f"wrong type of argument; it`s can`t be [{val}]; try [{ccd[0]}.{par} list]"
            rez = "success"
        try:
            self.data[par] = val
        except Exception as ex:
            return f"error: {ex}"
        self.save()
        return rez

    def user_get_com(self, command):
        ccd = command.split(".")
        if len(ccd) != 2:
            return "error: invalid command length; try [get help]"
        if ccd[1] not in self.data.keys():
            return f"wrong setting: no match for [{ccd[1]}] in {ccd[0]}"
        return f"{ccd[1]} = {self.data[ccd[1]]}"

    def help_command(self, command):
        si = "<LIS bot interface>\n"
        if command in self.help.keys():
            self.sender.messages.send(user_id=self.id, message=si + self.help[command], random_id=randint(1, 200000))
        else:
            self.sender.messages.send(user_id=self.id, message=si + f"no match for [{command}] in help list",
                                      random_id=randint(1, 200000))

    def add_phrase(self, mes):
        si = "<LIS bot interface>\n"
        if len(mes.split()) == 2:
            w1, w2 = mes.split()
            self.sender.messages.send(user_id=self.id, message=si + mor.sub_index(w1, w2, str(self.id))[1], random_id=randint(1, 200000))
        else:
            mess = si + "на данный момент бот в режиме обучения сети, используйте словосочетания из двух слов"
            self.sender.messages.send(user_id=self.id, message=mess, random_id=randint(1, 200000))

    def get_phrase(self, mes: str):
        global mor
        nous = r".,/?><'!`~\|[]{}()@#$%^&*_+№;%:*"
        sentence = "".join(filter(lambda gg: gg not in nous, list(mes)))
        return "\n".join(mor.get_words(sentence.split())[1])

    def delite_phrase(self, mes):
        global mor
        if self.id != ADMIN:
            return "You are not admin"
        return mor.delite_phrase(mes.split()[0], mes.split()[1])

    def get_all_data(self):
        global mor
        print(">>2")
        return mor.all_data()


class YandexTestTask:
    si = "<LIS YandexTestMode>\n"
    def __init__(self, user_id, message, sender, task):
        self.id, self.last_active, self.last_message = user_id, datetime.now(), message
        self.sender, self.help, self.counter_ban, self.active_ban = sender, {}, 0, datetime.now()
        self.set_pach, self.poj, self.new, self.task = f"users/{self.id}.data", "==", True, task.lower()
        self.tasks = {"запрос записи на стене": self.get_notes, 'запрос сортированные друзья': self.get_friends,
                      "бот большой брат": self.big_brother}
        user_get, self.nsls = sender.users.get(user_ids=(user_id))[0], False
        name = "traveler" if 'first_name' not in user_get.keys() else user_get['first_name']
        self.data = {'notify': "False", 'local_name': name}
        self.data_re = {'notify': lambda gr: gr in ["True", "False"], 'local_name': lambda gr: True}
        if os.path.exists(self.set_pach):
            self.new = False
            self.import_set()

    def import_set(self):
        self.procreate(self.set_pach)
        with open(file=self.set_pach, mode="r+", encoding=ENC) as file:
            for i in file.readlines():
                i = i.rstrip("\n")
                arg, rez = i.split(self.poj)
                self.data[arg] = rez

    def save(self):
        with open(file=self.set_pach, mode="w+", encoding=ENC) as file:
            rez = list(map(lambda i: f"{i}{self.poj}{self.data[i]}", self.data.keys()))
            file.write("\n".join(rez))

    def save_list(self, patch, lis):
        with open(file=patch, mode='w+', encoding=ENC) as file:
            file.write("\n".join(lis))

    def try_init(self) -> bool:
        si = "<LIS YandexTestMode>\n"
        if is_banned(self.id):
            return False
        for na, va in map(lambda g: g.split(self.poj), self.deparse("settings/helplist.txt")):
            self.help[na] = "\n".join(va.split("\\n"))
        if str(self.id) in BlackList:
            return False
        if self.task not in self.tasks.keys():
            req = sorted(self.tasks.keys(), reverse=False, key=lambda wo: distance(wo, self.task))
            mes = si + f"Не найдено, это случаем не 'switch yandex {req[0]}'? [да]-[нет]"
            self.nsls = True
        else:
            mes = si + f"Hi, {self.data['local_name']}!✨\nYou are in YandexTestMode. Type 'off' to exit."
        self.sender.messages.send(user_id=self.id, message=mes, random_id=randint(1, 200000))
        return True

    def procreate(self, patch):
        if not try_open(patch):
            with open(file=patch, mode='w+', encoding=ENC) as fi:
                pass

    def deparse(self, patch):
        self.procreate(patch)
        with open(file=patch, mode='r+', encoding=ENC) as file:
            rez = list(map(lambda i: i.rstrip("\n"), file.readlines()))
        return rez

    def command_selector(self, command):
        si = "<LIS YandexTestMode>\n"
        fl, self.last_active = is_banned(self.id), datetime.now()
        tf = (datetime.now() - self.active_ban) > timedelta(minutes=1)
        if not fl:
            if self.counter_ban == 0 or self.counter_ban < 1:
                self.active_ban, self.counter_ban = datetime.now(), 1
            elif self.counter_ban > 0 and not tf:
                self.counter_ban += 1
            if tf:
                self.counter_ban = 0
            if self.counter_ban > 10:
                ban(self.id)
                self.counter_ban = 0
                self.sender.messages.send(user_id=self.id, message=si + "you are banned for 20 minutes",
                                          random_id=randint(1, 200000))
        print(command)
        if not fl and self.nsls:
            if command.lower() in ['yes', 'run', 'да']:
                self.task = sorted(self.tasks.keys(), reverse=False, key=lambda wo: distance(wo, self.task))[0]
                self.nsls, command = False, "run"
            elif "switch" not in command:
                command = "off"
        if ("help" in command or "info" == command or "list" in command) and not fl:
            self.help_command(command)
        elif "off" == command:
            self.sender.messages.send(user_id=self.id, message=si + "finishing testing mode!", random_id=randint(1, 200000))
            Users.pop(str(self.id))
        elif "switch yandex " in command and not fl:
            Users[str(self.id)] = YandexTestTask(self.id, command, self.sender, command.lstrip("switch yandex "))
        elif not fl:
            self.tasks[self.task](command)

    def help_command(self, command):
        si = "<LIS YandexTestMode>\n"
        if command in self.help.keys():
            self.sender.messages.send(user_id=self.id, message=si + self.help[command], random_id=randint(1, 200000))
        else:
            self.sender.messages.send(user_id=self.id, message=si + f"no match for [{command}] in help list",
                                      random_id=randint(1, 200000))

    def get_notes(self, com):
        if "run" not in com:
            self.sender.messages.send(user_id=self.id, message=self.si + "use 'run' to start code or 'off' to exit", random_id=randint(1, 200000))
            return 0
        posts, rez = self.sender.wall.get(owner_id=str(ADMIN), count=5)['items'], []
        for ip in range(3 if len(posts) >= 3 else len(posts)):
            post = posts[ip]
            time = datetime.utcfromtimestamp(int(post['date'])).strftime('date: {%Y-%m-%d} time:{%H:%M:%S}')
            rez.append("{" + f"{post['text']}" + "};\n" + time)
        self.sender.messages.send(user_id=self.id, message=self.si + "3 latest's posts:\n" + "\n<-------------->\n".join(rez), random_id=randint(1, 200000))
        return 1

    def get_friends(self, com):
        if "run" not in com:
            self.sender.messages.send(user_id=self.id, message=self.si + "use 'run' to start code or 'off' to exit",
                                      random_id=randint(1, 200000))
            return 0
        fr = self.sender.friends.get(fields="bdate")
        rez = []
        if fr['items']:
            for i in sorted(fr['items'], reverse=False, key=lambda gg: gg['last_name']):
                bir = i['bdate'] if "bdate" in i.keys() else "NOT STATED"
                rez.append(f"friend-id: {i['id']};\nФамилия: {i['last_name']};\nИмя: {i['first_name']};\nДень рождения: {bir};")
        self.sender.messages.send(user_id=self.id, message=self.si + "ALL FRIENDS:\n", random_id=randint(1, 200000))
        for i in limited_text_split(4000, "\n<-------------->\n".join(rez), splittor="\n"):
            self.sender.messages.send(user_id=self.id, message=i, random_id=randint(1, 200000))

    def big_brother(self, com):
        town = "\n"
        response = self.sender.users.get(user_id=self.id, fields="city")
        if 'city' in response:
            town += f"Как там {response['city']['title']}?"
        return f"Привет, {self.data['local_name']}!" + town


def work_with_user(event, vk):
    text = event.text
    if event.user_id == ADMIN:
        if "/" in text:
            text = text.lstrip("/")
        else:
            return True
    if str(event.user_id) in GrayList and text != "on":
        return True
    if str(event.user_id) not in Users.keys():
        print(str(event.user_id) + " session started")
        use = User_session(event.user_id, text, vk)
        rez = use.try_init()
        if rez:
            Users[str(event.user_id)] = use
    if str(event.user_id) in Users.keys():
        Users[str(event.user_id)].command_selector(text)


def do_saves():
    global Users
    for i, us in Users.items():
        us.save()


def notify_if_need(vk):
    si = "<LIS bot interface>\nHi! Bot successfully started again.\n"\
         "(your user.notify=True; send [set user.notify False] to switch them off)"
    for user in filter(lambda gg: gg.endswith(".data"), os.listdir("users")):
        idd = user.split(".")[0]
        with open(file="users/" + user, mode="r+", encoding=ENC) as file:
            for i in file.readlines():
                if i.rstrip("\n") == "notify==True" and idd not in BlackList and idd not in GrayList:
                    vk.messages.send(user_id=user.split(".")[0], message=si, random_id=randint(1, 200000))
                    print(user.split(".")[0] + " notified successfully")
                    continue


def main_connect():
    global RUN, RETR
    RETR += 1
    si = "<LIS bot interface>\n"
    vk_session = vk_api.VkApi(token=my_token)
    longpoll = VkLongPoll(vk_session)
    vk = vk_session.get_api()
    time = f"storyteller started\n{datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\nretries: {RETR}"
    print(time)
    if RETR == 1:
        notify_if_need(vk)
    vk.messages.send(user_id=654275850, message=si + time, random_id=randint(1, 200000))
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me and event.text:
            if event.from_user and str(event.user_id) not in BlackList:
                work_with_user(event, vk)
            if event.text == 'shutdown' and event.user_id == ADMIN:
                print("buy")
                mor.off()
                vk.messages.send(user_id=654275850, message=si + "bye", random_id=randint(1, 200000))
                RUN = False
                do_saves()
                exit()


def except_hook(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)


if __name__ == "__main__":
    timer = Timer(10)
    sys.excepthook = except_hook
    while RUN:
        if timer.tk():
            try:
                main_connect()
            except requests.exceptions.ConnectionError:
                print("connection error")
            except Exception as ex:
                print(ex)

import requests
import os
import sys
import logging
import yaml
import secrets
import getopt


URL = "<URL>"
TOKEN = os.getenv('ART_TOKEN')
SETTINGS = './test.yaml'
REPO_TYPES = {"pypi":"simple-default",
              "docker":"simple-default",
              "generic":"simple-default",
              "rpm":"simple-default",
              "npm":"npm-default",
              "nuget":"nuget-default",
              "maven":"maven-2-default"}
FORMAT = '%(asctime)s %(funcName)s %(levelname)s:   %(message)s'
headers = {'X-JFrog-Art-Api' : TOKEN}
logging.basicConfig(level=logging.DEBUG, format=FORMAT)

def existsException(rtype=""):
    try:
        isinstance(rtype, str)
    except Exception as error:
        raise RuntimeWarning(rtype + " already exists !")

class Client():
    def __init__(self):
        self.url = URL
        self.token = TOKEN
        self.headers = {'X-JFrog-Art-Api' : TOKEN}


class Repo(Client):
    ''' Repo creation class

        Attributes:
            (self, rclass="local" *str, rtype="rpm" *str, rdesk="" *str, rnotes="" *str)
    '''
    def __init__(self,name,rclass="local", rtype="rpm", rdesk="", rnotes=""):
        super(Repo, self).__init__()
        self.name = name
        self.rclass = rclass
        self.rtype = rtype
        self.rdesk = rdesk
        self.rnotes = rnotes

    def __getStatus(self):
        self.url = URL + 'repositories/' + self.name
        req = requests.get(url=self.url, headers=self.headers)
        return req.status_code

    def isExists(self):
        ''' Returns bool'''
        return self.__getStatus() == 200

    def create(self):
        ''' Returns repo name *str'''
        if self.isExists():
            logging.warning("Repo %s already exists !", self.name)
            return False
        elif self.rtype not in REPO_TYPES:
            raise Exception(self.rtype + " wrong repo type !")
        else:
            data = {'key':self.name, 'rclass':self.rclass, 'packageType':self.rtype, 'description':self.rdesk, 'notes':self.rnotes, 'propertySets':["artifactory"], 'repoLayoutRef':REPO_TYPES[self.rtype]}
            req = requests.put(url=self.url, headers=self.headers, json=data)
            if req.status_code == 200:
                logging.info("Repo %s is created !", self.name)
                logging.debug('%s', req.text)
                return self.name
            else:
                raise Exception("Repo " + self.name + " can't be created !\n" + req.text)

    def remove(self):
        if self.isExists():
            req = requests.delete(url=self.url, headers=self.headers)
            if req.status_code == 200:
                logging.info("Repo %s has been deleted!", self.name)
                return True
            else:
                raise Exception(req.text)
        else:
            logging.warning("Repo %s doesn't exists!", self.name)
            return False


class Group(Client):
    def __init__(self, name):
        super(Group, self).__init__()
        self.name = name
        self.url = URL + 'security/groups/' + self.name

    def __getStatus(self):
        req = requests.get(url=self.url, headers=self.headers)
        return req.status_code

    def isExists(self):
        return self.__getStatus() == 200

    def create(self):
        ''' Returns group name *str '''
        if self.isExists():
            logging.warning("Group %s already exists !", self.name)
            return False
        data = {'name':self.name, 'description':"", 'realm':"ARTIFACTORY"}
        req = requests.put(url=self.url, headers=self.headers, json=data)
        if req.status_code == 201:
            logging.info("Group %s is created !", self.name)
            logging.debug('%s', req.text)
            return self.name
        else:
            raise Exception("Group " + self.name + " can't be created !\n" + req.text)

    def remove(self):
        if self.isExists():
            req = requests.delete(url=self.url, headers=self.headers)
            if req.status_code == 200:
                logging.info("Group %s has been deleted!", self.name)
                return True
            else:
                raise Exception(req.text)
        else:
            logging.warning("Group %s doesn't exists!", self.name)
            return False

class Permission(Client):
    def __init__(self,name):
        super(Permission, self).__init__()
        self.name = name
        self.url = URL + 'security/permissions/' + self.name      

    def __getStatus(self):
        req = requests.get(url=self.url, headers=self.headers)
        return req.status_code

    def isExists(self):
        return self.__getStatus() == 200

    def create(self, repo):
        ''' Returns permission name *str
            Attributes:
                repo *str - needed for permission assigning
        '''
        self.repo = repo
        if self.isExists():
            logging.warning("Permission %s already exists !", self.name)
            return False
        else:
            data = {'name':self.name, 'repositories': [self.repo], 'principals' : {'groups' : {self.name : [ "r", "d", "w", "n" ]}}}
            req = requests.put(url=self.url, headers=self.headers, json=data)
            if req.status_code == 201:
                logging.info("Permission %s is created !", self.name)
                logging.debug('%s', req.text)
                return self.name
            else:
                raise Exception("Permission " + self.name + " can't be created !\n" + req.text)

    def remove(self):
        if self.isExists():
            req = requests.delete(url=self.url, headers=self.headers)
            if req.status_code == 200:
                logging.info("Permission %s has been deleted!", self.name)
                return True
            else:
                raise Exception(req.text)
        else:
            logging.warning("Permission %s doesn't exists!", self.name)
            return False

class User(Client):
    def __init__(self):
        super(User, self).__init__()
        self.valid_users = {}
        self.password = genPass()

    def __validUsers(self, users):
        if not isinstance(users,list):
            raise Exception("Passing argument should be a list!")
        for user in users:
            url = URL + 'security/users/' + user
            req = requests.get(url=url, headers=self.headers)
            if req.status_code == 200:
                self.valid_users.update({user:dict(req.json())})
            else:
                logging.info("%s doesn't exists !", user)
                logging.debug('%s', req.text)
        return self.valid_users

    def isExists(self, user):
        url = URL + 'security/users/' + user
        req = requests.get(url=url, headers=self.headers)
        return req.status_code == 200

    def create(self, user, ci=False, email="devnull@example.ru"):

        if ci:
            user = user + "-ci"
            data = {'name':user, "email":email, 'disableUIAccess': True, 'internalPasswordDisabled': False, 'groups': ["readers"], 'password': self.password, 'profileUpdatable': False}
        else:
            data = {'name':user, "email":email, 'disableUIAccess': False, 'internalPasswordDisabled': False, 'groups': ["readers"], 'password': self.password}    
        if self.isExists(user):
            logging.warning("User %s already exists !", user)
            return False
        url = URL + 'security/users/' + user
        req = requests.put(url=url, headers=self.headers, json=data)
        if req.status_code == 201:
            logging.info("%s is created !", user)
            return user
        else:
            raise Exception(req.text)

    def remove(self, user):
        if self.isExists(user):
            url = URL + 'security/users/' + user
            req = requests.delete(url=url, headers=self.headers)
            if req.status_code == 200:
                logging.info("%s has been deleted", user)
                return True
            else:
                raise Exception(req.text)
        else:
            logging.warning("User %s doesn't exists!", user)
            return False

    def addToGroup(self, users, group):
        for user, value in self.__validUsers(users).items():
            value['groups'].append(group)
            url = URL + 'security/users/' + user
            data = value
            req = requests.post(url=url, headers=self.headers, json=data)
            if req.status_code == 200:
                logging.info("%s successfully added to group %s", user, group)
                logging.debug('%s', req.text)
            else:
                logging.error("Can't add %s to %s", user, group)
        return True

    def createAPIkey(self, user):
        if self.isExists(user):
            url = URL + 'security/apiKey'
            req = requests.post(url=url, auth=(user, self.password))
            if req.status_code == 201:
                logging.debug(req.text)
                return req.json()['apiKey']
            else:
                raise Exception(req.text)
        else:
            raise Exception(user + " doesn't exists !")

    def getToken(self, user):
        if self.isExists(user):
            url = URL + 'security/token'
            headers = self.headers
            headers.update({'Content-Type': 'application/x-www-form-urlencoded'})
            data = {'username':user, 'expires_in': 0}
            req = requests.post(url=url, headers=headers, data=data)
            if req.status_code == 201:
                logging.info("%s", req.text)
                logging.info(req.json()['expires_in'])
                return req.json()['access_token']
            elif req.status_code == 200:
                logging.info("%s", req.text)
                return req.json()['access_token']
            else:
                raise Exception(req.text)
        else:
            raise Exception(user + " doesn't exists !")

'''=========================================================================================================================================='''


'''
User functions bellow
'''

def settings_loader(settings_path="settings.yaml"):
    with open(settings_path) as settings:
        repos = yaml.safe_load(settings)
    return repos

def genPass(length=12, charset="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*()"):
    return "".join([secrets.choice(charset) for _ in range(0, length)])

def createLocalRepo(name, users, responsible="", ticket_id="", rtype="rpm", ci=False):
    repo = Repo(name=name, rtype=rtype, rdesk="Responsible: "+responsible, rnotes=ticket_id)
    group = Group(name)
    perm = Permission(name)
    user = User()
    try:
        repo.create()
        group.create()
        perm.create(repo=name)
        if ci:
            ci_user = user.create(user=name, ci=True)
            if ci_user:
                users.append(ci_user)
                user.addToGroup(users, name)
                token = user.createAPIkey(ci_user)
                return {"Repo":name, "Group":name, "Permission":name, "User":ci_user, "Token":token}
        return {"Repo":name, "Group":name, "Permission":name}
    except Exception as err:
        logging.error(err)

def removeLocalRepo(name):
    perm = Permission(name)
    group = Group(name)
    repo = Repo(name)
    user = User()
    try:
        perm.remove()
        group.remove()
        repo.remove()
        return True
    except Exception as err:
        logging.error(err)


'''======================================================================================================================================='''


if __name__ == "__main__":

    try:
        opts, args = getopt.getopt(sys.argv[1:], "-nht:-r:-R:", ["new", "help", "token=", 'remove_user=', 'remove_repo='])
    except getopt.GetoptError as error:
        logging.error(error)
        sys.exit(2)

    for o, a in opts:
            if o in ("-h", "--help"):
                print("coming soon...")
            elif o in ("-n", "--new"):
                repo = settings_loader()
                repo_name = next(iter(repo))
                repo_values = repo[repo_name]
                logging.debug(type(repo_values['ci']))

                logging.info(createLocalRepo(name=repo_name, users=repo_values['participants'], responsible=repo_values['responsible'], ticket_id=repo_values['ticket_id'], rtype=repo_values['repo_type'], ci=repo_values['ci']))
            elif o in ("-t", "--regenerate_token"):
                user = User()
                try:
                    user.getToken(a)
                except Exception as err:
                    logging.error(err)
            elif o in ("-r", "--remove_user"):
                user = User()
                try:
                    user.remove(a)
                except Exception as err:
                    logging.error(err)
            elif o in ("-R", "--remove_repo"):
                removeLocalRepo(a)
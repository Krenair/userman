import ldap, types
import sr_ldap
import srusers

# Get a list of all groups
def list():
    l = sr_ldap.conn
    sr_ldap.bind()

    g_res = l.search_st( "ou=groups,o=sr",
                         ldap.SCOPE_ONELEVEL,
                         filterstr="(objectClass=posixGroup)" )

    groups = [x[1]["cn"][0] for x in g_res]

    return groups

class group:
    """A group of users"""

    def __init__( self, name ):
        """Initialise the group object.
        Args: name = the name of the group"""
        self.l = sr_ldap.conn
        sr_ldap.bind()

        self.name = name

        #List of new users
        self.new_users = []

        #List of removed users
        self.removed_users = []

        if not self.__load(name):
            #Have to create new
            self.gid = self.__get_new_gidNumber()
            self.in_db = False
            self.members = []
            self.dn = "cn=%s,ou=groups,o=sr" % (name)
        else:
            self.in_db = True

    def __load(self, name):
        info = self.l.search_st( "ou=groups,o=sr",
                                 ldap.SCOPE_ONELEVEL,
                                 filterstr="(&(objectClass=posixGroup)(cn=%s))" % ( name ) )
        
        if len(info) == 1:
            self.dn = info[0][0]
            self.gid = info[0][1]["gidNumber"]
            if "memberUid" in info[0][1].keys():
                self.members = info[0][1]["memberUid"]
            else:
                self.members = []
            return True
        else:
            return False

    def user_add(self,users):
        """Add a user to the group"""
        if users.__class__ is srusers.user:
            users = [user.username]
        elif type(users) is not types.ListType:
            users = [users]
        
        for user in users:
            if user not in self.members:
                self.members.append( user )
                self.new_users.append( user )

    def user_rm(self,users):
        """Remove a user from a group"""
        if users.__class__ is srusers.user:
            users = [user.username]
        elif type(users) is not types.ListType:
            users = [users]
            
        for user in users:
            if user in self.members:
                self.members.remove(user)
                self.removed_users.append(user)

    def rm(self):
        """Delete the group"""
        if not self.in_db:
            raise "Cannot delete group - doesn't exist"
        else:
            self.l.delete_s( self.dn )
            self.in_db = False
            return True
    
    def save(self):
        """Save the group"""
        if self.in_db:
            return self.__update()
        else:
            return self.__save_new()

    def __save_new(self):
        modlist = [ ("objectClass", "posixGroup"),
                    ("cn", self.name),
                    ("gidNumber", str(self.gid)) ]

        if len(self.members) > 0:
            modlist.append( ("memberUid", self.members) )

        self.l.add_s( self.dn, modlist )

        self.in_db = True
        self.new_users = []
        self.removed_users = []
        return True

    def __update(self):
        if len(self.new_users) == 0 and len(self.removed_users) == 0:
            return True

        modlist = [ ( ldap.MOD_REPLACE,
                      "memberUid",
                      self.members ) ]

        self.l.modify_s( self.dn, modlist )

        self.new_users = []
        self.removed_users = []
        
    def __get_new_gidNumber( self ):
        """Finds the next available GID"""
        groups = self.l.search_st( "ou=groups,o=sr",
                                   ldap.SCOPE_ONELEVEL,
                                   filterstr = "(objectClass=posixGroup)",
                                   attrlist = ["gidNumber"] )
        gids = []

        for gid in [int(x[1]["gidNumber"][0]) for x in groups]:
            gids.append(gid)

        gid = 3000
        while gid in gids:
            gid += 1

        return gid
            
    def __str__(self):
        desc = ""

        desc = desc + "Group: %s\n" % (self.name)
        desc = desc + "gid: %s\n" % (str(self.gid))
        desc = "%i members: " % ( len(self.members) )

        desc = desc + ", ".join( self.members )

        return desc
            


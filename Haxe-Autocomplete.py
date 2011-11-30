import sublime, sublime_plugin

import subprocess
import types
import re
import os

from xml.etree import ElementTree as ET
from urllib import urlopen

GOOGLE_AC = r"http://google.com/complete/search?output=toolbar&q=%s"


count = 0;

def formatSignature(sig):
    fmt = re.sub("->",",", sig)
    fmt = re.sub("(.*), ([A-Za-z0-9]+$)","(\\1):\\2", fmt)
    fmt = re.sub("\s", "", fmt)
    fmt = re.sub(",",", ", fmt)

    return fmt


last_build_cmd = None

previous_builds = {}

#Simply does last build
class HaxeBuildCommand(sublime_plugin.WindowCommand):
    def run(self):
        global last_build_cmd
        print "Preparing"
        if last_build_cmd != None:
            projectPath = self.window.folders()[0]
            self.window.run_command("save_all");
            self.window.run_command("exec",{"cmd": last_build_cmd, "working_dir" : projectPath, "file_regex": "(.+):([0-9]+): characters ([0-9]+-[0-9]+) : (.*)$" })
        else:
            print "No default build"

#build tool
class HaxeBuildToolCommand(sublime_plugin.WindowCommand):
    mode_types = ["debug","release"]
    os_types = ["mac","flash"]

    cur_mode = ""           #debug or release
    cur_type = ""           #nmml or hxml
    cur_cfg = ""            #something.nmml or something.hxml
    cur_os = ""             #mac flash


    nmmls = []
    hxmls = []
    def run(self):
        self.nmmls = self.get_list_ext("nmml")
        self.hxmls = self.get_list_ext("hxml")

        #self.gen_mru_prompt()
        self.mru_build()

    def mru_build(self):
        global previous_builds
        items = [["Last build","Sample Custom build"], ["Custom build","New ant/nmml/hxml build"]]

        for build in previous_builds:
            s = ""
            for bpart in previous_builds[build]:
                s += bpart + " "
            items.append( s )

        def _callback(idx):
            if idx == -1:
                return
            elif items[idx][0] == "Last build":
                self.window.run_command("haxe_build")
            elif items[idx][0] == "Custom build":
                self.type_build()
            else:
                projectPath = self.window.folders()[0]
                self.window.run_command("save_all");
                self.window.run_command("exec",{"cmd": previous_builds[idx-2], "working_dir" : projectPath, "file_regex": "(.+):([0-9]+): characters ([0-9]+-[0-9]+) : (.*)$" }) 
            return

        self.window.show_quick_panel (items, _callback)

    def type_build(self):
        items = ["Ant", "Hxml"] #, "Nmml"]

        def _callback(idx):
            if idx == -1:
                return
            elif items[idx] == "Ant":
                print "ANT"
                self.menu_antbuild()
            elif items[idx] == "Hxml":
                print "HXML"
                self.menu_hxml_build()
            #elif items[idx] == "Nmml":
            #    print "NMML"
            return

        self.window.show_quick_panel (items, _callback)

    def menu_hxml_build(self):
        items = self.hxmls

        def _callback(idx):
            global last_build_cmd, previous_builds
            if idx == -1:
                return
            else:
                projectPath = self.window.folders()[0]

                #Make sure to run this under self.window!!!! (not view)
                print "hxml: " + str(items[idx])
                last_build_cmd = ["haxe",items[idx]]
                previous_builds[str(last_build_cmd)] = last_build_cmd
                self.window.run_command("exec",{"cmd": last_build_cmd, "working_dir" : projectPath, "file_regex": "(.+):([0-9]+): characters ([0-9]+-[0-9]+) : (.*)$" })
                
            return

        self.window.show_quick_panel(items, _callback)


    def menu_antbuild(self):

        items = ["Launch","Filler"]

        def _callback(idx):
            global last_build_cmd, previous_builds
            if idx == -1:
                return
            elif items[idx] == "Launch":
                projectPath = self.window.folders()[0]

                #Make sure to run this under self.window!!!! (not view)
                last_build_cmd = ["ant"]
                previous_builds[str(last_build_cmd)] = last_build_cmd
                self.window.run_command("exec",{"cmd":last_build_cmd, "working_dir" : projectPath })
                
            elif items[idx] == "Other targets....":
                print "Filler!"
            return

        self.window.show_quick_panel(items, _callback)

    def gen_mru_prompt(self):
        oplist = []
        if self.cur_cfg != "":
            if self.cur_mode != "":
                oplist.append(["Last Build", self.cur_cfg + " " + self.cur_mode])
        
        oplist.append(["New Build"])
                
        self.window.show_quick_panel(oplist, self.process_mru)

        print dir(self.window)

    def process_mru(self, idx):
        print str(idx)
        if idx == -1:
            return

        if self.cur_cfg != "":
            if self.cur_mode != "":
                if idx == 0:
                    self.build_current()
                    return

        self.gen_nmml_prompt()

    def gen_nmml_prompt(self):
        self.window.show_quick_panel(self.nmmls, self.gen_nmml_debug_prompt)

    def gen_nmml_debug_prompt(self, idx):
        if idx == -1:
            return

        self.cur_cfg = self.nmmls[idx]
        self.cur_type = "nmml"
        self.window.show_quick_panel(["Debug","Release"], self.gen_nmml_platform_prompt)

    def gen_nmml_platform_prompt(self, idx):
        if idx == -1:
            return

        self.cur_mode = self.mode_types[idx]
        self.window.show_quick_panel(["Mac","Flash"], self.sel_mode)

    def sel_mode(self, idx):
        if idx == -1:
            return

        self.cur_os = self.os_types[idx]

        self.build_current()



    def build_current(self):
        cmd = ""
        if self.cur_type == "nmml":
            cmd = "haxelib run nme test " + self.cur_cfg + " " + self.cur_os + " "
            if self.cur_mode == "debug":
                cmd += "-Ddebug"
            
        elif self.cur_type == "hxml":
            True
        else:
            print "cur_type is an invalid value: " + self.cur_type

        #self.window.active_view().run_command("haxe_build",{"cmd":cmd})

        projectPath = self.window.folders()[0]
        self.window.active_view().run_command("exec",{"cmd":cmd, "working_dir" : projectPath})

    def get_list_ext(self, ext):
        projectPath = self.window.folders()[0]

        files = os.listdir(projectPath)
        print "dir: " + str(files)

        pf = [];

        for file in files:
            if self.has_ext(file, ext):
                pf.append(file)

        return pf

    def has_ext(self, s, ext):
        match = re.match(".*\."+ext+"$", s)
        if match is not None:
            return True
        return False

class haxeImportCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        print self.view.word( 4 )
        print self.view.substr( self.view.word( self.view.sel()[0] ))
        return

def on_done(self, num):
    return


completions = []
lpos = -1;

def is_valid_ac(str):
    if is_valid_str(str):
        if str[0] == "<":
            return True
    return False

def is_valid_str(str):
    if len(str) > 0:
        return True
    return False


def cccompletion( ccident ):
    rstring = "$"

    l = 0

    while l < len(ccident):
        rstring += ccident[l] + "[a-z_0-9]+"
        l += 1
    rstring = "$"

    for c in completions:
        if not (re.match("[A-Za-z0-9\\.]*") == None):
            #We've found acceptable autcomplete
            print "found"
    return

#uuuuuugh
def haxe_display_complete(view, pos, fname):
    global completions
    lines = len(view.lines(sublime.Region(0,pos)))
    unx_pos = pos;
    win_pos = pos + lines - 1;

    view.run_command("save")

    print str(unx_pos) + " : " + str(win_pos)

    projectPath = view.window().folders()[0];

    cmd = "haxe project.hxml --display " + fname + "@"

    ## WINDOWS HACK ##
    kwargs = {}
    if subprocess.mswindows:
        su = subprocess.STARTUPINFO()
        su.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        su.wShowWindow = subprocess.SW_HIDE
        kwargs['startupinfo'] = su

    print cmd

    ## FIX FOR LINE ENDINGS
    proc_mac = subprocess.Popen(cmd+str(unx_pos), shell=True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, stdin=subprocess.PIPE, cwd=projectPath)
    proc_win = subprocess.Popen(cmd+str(win_pos), shell=True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, stdin=subprocess.PIPE, cwd=projectPath) #, **kwargs)
    #p = subprocess.Popen("haxe -cp "+projectPath+" --display /Users/matthew/Documents/Workspace/sublime-plugin-testing/HelloWorld/src/Main.hx@57", shell=True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
    
    res_mac = proc_mac.communicate()[0] #block here
    res_win = proc_win.communicate()[0]


    print "mac: " + res_mac
    print "win: " + res_win

    if len(res_mac) == 0:
        res_mac = res_win
    elif res_mac[0] != "<":
        res_mac = res_win


    print is_valid_ac(res_mac)
    print is_valid_str(res_mac)

    if not is_valid_ac(res_mac) and is_valid_str(res_mac):
        #It's an error
        print "Your build has an error that is preventing autocomplete!"
        completions = [];
        return
    
    if not is_valid_str(res_mac):
        print "No results"
        completions = [];
        return
    


    disp_xml = res_mac
            
    xmlout =  ET.fromstring(
                    disp_xml
                )

    #print "XML: " + ET.tostring(xmlout)

    elements = xmlout

    #print "TBALE"

    s = []

    haxeTypes = xmlout.getiterator("type")
    stcomp = ""
    first = True
    for hxtype in haxeTypes:
        if first == False:
            stcomp += ", "
        stcomp += hxtype.text
        first = False
        s.append( ( hxtype.text, hxtype.text ) )

    for el in elements:
        hcmp = el.attrib["n"]
        for e in el.getiterator("t"):
            if e.text == None:
                hdtl = ""
            else:
                hdtl = formatSignature (e.text)
            s.append( (hcmp + " " + str(hdtl), hcmp ) )

    #return s
    return s;

#def complete_all(view)
#    pos = 

#@param str 0 -> current pos
#@return -1 if not dot word, pos of . if is dot word
def is_dot_word(str):
    i = len(str)-1

    while i >= 0:
        match = re.match("[A-Za-z0-9_]", str[i])
        if match is None:
            break
        i -= 1;
    
    if str[i] != ".":
        i = -1;

    return i


def find_opening_bracket(str):
    pos = len(str)-1

    nestedbrk = 1
    rval = -1


    while pos > 0:
        if str[pos] == ")":
            nestedbrk += 1
        elif str[pos] == "(":
            nestedbrk -= 1
    
        if nestedbrk == 0:
            rval = pos
            break
        
        pos -= 1

    return rval


dirty_completion = False

def try_auto_complete(view):
    global completions, lpos, dirty_completion

    fname = view.file_name()
    pos = view.sel()[0].begin()

    print "Word is: " + view.substr(view.word( pos ));

    text = view.substr(sublime.Region(pos - 1, pos))
    ftext = view.substr(sublime.Region(0,pos))

    dword_pos = is_dot_word(ftext)+1;
    dword_is = dword_pos != 0

    print "dot_word: " + str(is_dot_word(ftext))

    #if True:    #If INSERT/NOHIST
    if not hasattr(view, 'command_history') or view.command_history(0)[0] == 'insert' or view.command_history(0)[0] == "insert_snippet":
        if dword_is == True:
            #print "Dot word!"
            if lpos != dword_pos or text == ".":
                #view.run_command('hide_auto_complete')
                print "Gen completion"
                completions = haxe_display_complete(view,dword_pos,fname)
                dirty_completion = True
            
            lpos = dword_pos
            #print "DCL: " + str(dirty_completion)
            if len(completions) != 0 and dirty_completion == True:
                view.run_command('auto_complete', {'disable_auto_insert': True})
                dirty_completion = False;
                #print "Running ATC"
        else:
            #print "Hide Completion"
            view.run_command('hide_auto_complete')

        print "ts_branch: "
        if text == "(":
            #Do function signature completion
            cfuncsig = find_opening_bracket(ftext)
            #print "cfuncsig: " + str(cfuncsig)
            if cfuncsig != -1:
                sig = str(haxe_display_complete(view,cfuncsig+1,fname)[0][0])
                #print "sig"
                #print sig
                view.set_status( 'Function-def', formatSignature(sig) )
            else:
                view.set_status( 'Function-def', '' )
    else:
        #print "Hide Completion"
        dirty_completion = True
        view.run_command('hide_auto_complete')


    
    
    return

def is_haxe_lang(view):
    lang = os.path.splitext(os.path.basename(view.settings().get('syntax')))[0]
    return lang == "HaXe"

class HaXeAutoComplete(sublime_plugin.EventListener):

    def on_modified(self, view):
        if not is_haxe_lang(view):
            return
        try_auto_complete(view)

        view_to_pack(view, "BitmapData")

    def on_query_completions(self, view, prefix, locations):
        global completions
        if not is_haxe_lang(view):
            return

        fname = view.file_name()
        pos = view.sel()[0].begin()
        text = view.substr(sublime.Region(pos - 1, pos))

        return completions



### @@@ DIRECTORY DIVING GOES HERE @@@ ###
def pack_to_packlist(str_pack):
    ## TEST
    if re.match("[A-Za-z0-9\\.]*") == None:
        print "Not a valid package: " + str(str_pack)
    return str_pack.split(".");

def view_to_pack(view, classname):
    #These re are crazy ugly. please fix.
    pack = view.find("import[ \\t]*([A-Za-z0-9\\.]*\\."+classname+")[ \\t]*;", 0)
    

    if pack != None:
        pck = re.match("import[ \\t]*([A-Za-z0-9\\.]*)[ \\t]*;", view.substr(pack)).group(1);
        print "pack: " + str(pck)


def ghl( a, b, 
        c, d):

    ghl( "a", "b", 
        "c", "d" )

    return



















#################################################################################################
####################### REFACTORING #############################################################
#################################################################################################

#Simply does last build
class HaxeRefactorCommand(sublime_plugin.TextCommand):
    def run(self, view):
        view = self.view
        spos = view.sel()[0].begin()
        word = view.substr(view.word(spos))
        left_word = self.find_left_word( spos )

        print "The word is: " + word
        print "The leftword is: " + left_word

        if left_word == "var":
            self.var_refactor( )
        elif left_word == "implements":
            self.extends_refactor( )

    
    def is_full_var_decl( self, pos ):


        return

    def find_left_word( self, pos ):
        #TODO add >0 check
        pos = self.view.word(pos).begin( ) - 1

        while self.view.substr( pos ) == " ":
            pos -= 1
        return self.view.substr( self.view.word( pos ) )



    def find_top_of_class( self, pos ):
        view = self.view;

        view.find_all()

        return



    def var_refactor( self ):
        items = [["Extract","Move declaration to class"],["Infer","Declare as inferred type"]];

        def _callback(idx):


            return
        
        self.view.window().show_quick_panel (items, _callback)

    
    def extends_refactor( self ):
        items = [["Implement methods","Generate all methods for the implementation"]];

        def _callback(idx):


            return
        
        self.view.window().show_quick_panel (items, _callback)










       	
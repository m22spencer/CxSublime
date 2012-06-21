import sublime, sublime_plugin
import re
import subprocess
from xml.etree import ElementTree as ET
import os

current_file = []
class HaxeBuildConfigCommand (sublime_plugin.WindowCommand):
	def run(self):
		def _cb(t_File):
			global current_file, last_completion_byte
			current_file = t_File
			last_completion_byte = -1
			return
		self.select_hxml_menu (_cb)

	def select_hxml_menu(self, _cb):
		hxml_list = fetch_files_of_ext (self.window.active_view (), "hxml")
		def _callback (idx):
			if idx == -1: return
			_cb (hxml_list[idx])

			


		avail = [];
		for h in hxml_list:
			mx = lchar = len (h[0])
			lchar -= 40;
			if lchar < 0: lchar = 0
			shortened = ""
			while lchar < mx: 
				shortened += h[0][lchar]
				lchar+=1
			avail.append ([shortened, h[1]])

		self.window.show_quick_panel (avail, _callback)
		return
class HaxeCompileCommand (sublime_plugin.WindowCommand):
	def run (self):
		simple_haxe_compile (self.window.active_view ())
		return

class HaxeGenerateImportCommand (sublime_plugin.TextCommand):  
	def run (self, edit):
		sig = self.find_import_signature ()
		ars_Imports = self.fetch_all_imports ()
		for imp in ars_Imports:
			#print imp[1] + ":" + sig
			if imp[1] == sig: return
		self.insert_new_import (ars_Imports, sig)
		return
	def fetch_all_imports (self):
		imports = self.view.find_all ("import.+?[A-Za-z0-9_]*;")
		out_imports = [];
		for region in imports:
			full = re.match ("import.+?([A-Za-z0-9_\.]+)", self.view.substr (region)).group (1)
			out_imports.append ((region,full))
			#out_imports.append (self.view.substr (imp))
		#print "Imports " + str(imports)
		#print "Out imports" + str(out_imports)
		return out_imports
	def insert_new_import (self, ars_ImportList, s_Import):
		lowest = 0;
		for rs_Import in ars_ImportList:
			if rs_Import[0].b > lowest:
				lowest = rs_Import[0].b;
		pack = self.view.find ("package .*?;", 0)
		if pack != None:
			lowest = pack.b + 1

		edit = self.view.begin_edit ()
		self.view.insert (edit, lowest, "\nimport " + s_Import + ";")	
		self.view.end_edit (edit) 
		return
	def find_import_signature (self):
		point = self.view.sel ()[0].begin ();
		impt = self.view.word (point);

		pos = impt.a;
		while pos >= 0 and re.match ("[A-Za-z0-9\.]+", self.view.substr (pos)):
			pos-=1;
		imptf = sublime.Region (pos+1, impt.b)

		full_import = self.view.substr (imptf)

		edit = self.view.begin_edit ()
		self.view.replace (edit, imptf,self.view.substr (impt))

		return full_import


class EventsHandler (sublime_plugin.EventListener):
	def on_modified (self,view):
		try_haxe_autocomplete (view, view.sel ()[0].begin ())
		#print last_completion_cache
		return
	
	def on_query_completions (self,view,prefix,locations):
		return last_completion_cache

def position_to_bytes (view, pos):
	if view.line_endings () == "Windows":
		pos += view.rowcol (pos)[0]
	return pos  

def run_process (s_Cwd,as_Command):
	cmd = "";
	for arg in as_Command:
		cmd += arg + " "
	proc = subprocess.Popen (cmd, shell=True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, stdin=subprocess.PIPE, cwd=s_Cwd)
	return proc.communicate()[0];
	
def a2s_xml_to_completions (xml_Completions):
	if len(xml_Completions) == 0:
		return []		#Error! Handle this properly
	if xml_Completions[0] != "<":
		return []		#Error! Handle this properly
	xml = ET.fromstring(xml_Completions)

	#print xml_Completions

	clist = []

	for cnode in xml:
		cname = cnode.attrib["n"]
		for ctype in cnode.getiterator("t"):
			if ctype.text == None: #package
				clist.append ((cname,cname))
			else:
				clist.append ((cname+":"+ctype.text,cname)) #property

	return clist

def simple_haxe_display_complete (view, pos, fname):
	global current_file

	view.window ().run_command("save_all") #FIXME have this save only existing files
	repaired_pos = position_to_bytes (view, pos)
	if len (current_file) < 2:
		view.window ().run_command ('build_config')
		return
		
	cwd = current_file[0]; 
	fname = "\"" + fname + "\""
	cmd = ["haxe ", current_file[1], "--display ", fname+"@"+str(repaired_pos), "-D", "use_rtti_doc"]
	ret = run_process (cwd, cmd)
	#print "Haxe complete" + ret
	return a2s_xml_to_completions (ret)

def simple_haxe_compile (view):
	global current_file

	view.window ().run_command("save_all") #FIXME have this save only existing files
	if len (current_file) < 2:
		view.window ().run_command ('haxe_build_config')
		return
		
	cwd = current_file[0]; 
	cmd = ["haxe ", current_file[1]]
	view.window ().run_command("exec",{
		"cmd": cmd, 
		"working_dir" : cwd, 
		"file_regex": "(.+):([0-9]+): characters ([0-9]+-[0-9]+) : (.*)$" })

	ret = run_process (cwd, cmd)
	print "Return: " + ret
	return

#Autocomplete main
last_completion_byte = -1
last_completion_cache = []
last_completion_dirty = True
def try_haxe_autocomplete (view, pos):
	global last_completion_cache, last_completion_byte, last_completion_dirty

	if not hasattr(view, 'command_history') or view.command_history(0)[0] == 'insert' or view.command_history(0)[0] == "insert_snippet":
		dot_byte = is_dot_completion (view,pos);
		if dot_byte != -1:
			#print "DB: " + str (dot_byte)
			if dot_byte != last_completion_byte:
				#we need to call the compiler and regenerate the cache
				#TODO last_completion_cache = haxe --display
				last_completion_cache = simple_haxe_display_complete (view, dot_byte, view.file_name ())
				#last_completion_cache = [("This is a test", "Test")]
				last_completion_dirty = True
				last_completion_byte = dot_byte
			
			if len(last_completion_cache) != 0 and last_completion_dirty == True:
				#print "Do autocomplete"
				view.run_command ('auto_complete', {'disable_auto_insert': True})
				last_completion_dirty = False;
			#print "Dot word!"
		else:
			0==0
			#print "Not Dot word"
			#view.run_command ('hide_auto_complete')

	else:
		last_completion_dirty = True
		#view.run_command ('hide_auto_complete')


	return


#Parsing
def is_dot_completion (view, pos):
 	bpos = -1
 	if view.substr (sym_left_word (view, pos)) == ".":
 		bpos = sym_left_word (view,pos)+1
 	elif view.substr (pos-1) == ".":
 		bpos = pos;
 	return bpos

def sym_left_word (view, pos):
	return view.word (pos).a-1;\

def fetch_files_of_ext (view, s_Ext):
	valid_files = []
	for path in view.window ().folders ():
		for root, dirs, files in os.walk (path):
			for fname in files:
				#fname = str (name)
				if is_ext (fname, s_Ext):
					valid_files.append ((root,fname))
	return valid_files

def is_ext (s_File, s_Ext):
	return re.match (".*\."+s_Ext+"$",s_File) != None

def extract_hxml (s_Hxml):
	return
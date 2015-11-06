# -*- coding: utf-8 -*-
import time
from collections import OrderedDict


# this is some strange form of python black magic
def station( implementation_name ):
	def cls_call( cls ):
		if not hasattr(cls, "_attributes"):
			cls._attributes = {}
		for name, method in cls.__dict__.iteritems():
			if hasattr(method, "_attributes"):
				method._attributes["callback"] = method
				cls._attributes[name] = method._attributes

		FSM.add_implementation( implementation_name, cls.get_attributes() )
		return cls
	return cls_call

# there is probably some way to even further clean this up with
# a metadecorator or something
def list_index( index ):
	def method_call( method ):
		if not hasattr(method, "_attributes"):
			method._attributes = {}
		method._attributes["list-index"] = index
		return method
	return method_call

def name( name ):
	def method_call( method ):
		if not hasattr(method, "_attributes"):
			method._attributes = {}
		method._attributes["name"] = name
		return method
	return method_call

def color( color ):
	def method_call( method ):
		if not hasattr(method, "_attributes"):
			method._attributes = {}
		method._attributes["color"] = color
		return method
	return method_call

def trigger_automatically( trigger_automatically ):
	def method_call( method ):
		if not hasattr(method, "_attributes"):
			method._attributes = {}
		method._attributes["trigger-automatically"] = trigger_automatically
		return method
	return method_call


class FSM( object ):
	current = ""
	fsm = {}

	@staticmethod
	def set_implementation( implementation_name ):
		FSM.current = implementation_name

	@staticmethod
	def get_implementation( ):
		return FSM.current

	@staticmethod
	def add_implementation( implementation_name, implementation ):
		if not FSM.fsm:
			FSM.current = implementation_name
		FSM.fsm[ implementation_name ] = implementation

	@classmethod
	def get_attributes( cls ):
		if hasattr(cls, "_attributes"):
			return cls._attributes
		else:
			return None

	@staticmethod
	def get_fsm( ):
		if not FSM.current in FSM.fsm:
			return None
		od =  OrderedDict(sorted( FSM.fsm[ FSM.current ].items(),
						key=lambda (k, v): v[ "list-index" ] ) )
		return od

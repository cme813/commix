#!/usr/bin/env python
# encoding: UTF-8

"""
This file is part of commix (@commixproject) tool.
Copyright (c) 2014-2016 Anastasios Stasinopoulos (@ancst).
https://github.com/stasinopoulos/commix

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
 
For more see the file 'readme/COPYING' for copying permission.
"""

import os
import sys
import urllib2

from src.utils import menu
from src.utils import logs
from src.utils import settings
from src.utils import session_handler

from src.thirdparty.colorama import Fore, Back, Style, init

from src.core.requests import headers
from src.core.requests import requests
from src.core.requests import parameters
from src.core.modules import modules_handler
from src.core.requests import authentication

from src.core.injections.results_based.techniques.classic import cb_handler
from src.core.injections.results_based.techniques.eval_based import eb_handler
from src.core.injections.blind.techniques.time_based import tb_handler
from src.core.injections.semiblind.techniques.file_based import fb_handler

"""
Command Injection and exploitation controller.
Checks if the testable parameter is exploitable.
"""

def check_for_stored_sessions(url, http_request_method):

  if not menu.options.ignore_session:
    if os.path.isfile(settings.SESSION_FILE) and not settings.REQUIRED_AUTHENTICATION:
      if not menu.options.tech:
        menu.options.tech = session_handler.applied_techniques(url, http_request_method)
      if session_handler.check_stored_parameter(url, http_request_method):
        settings.LOAD_SESSION = True
        return True

  if menu.options.flush_session:
    session_handler.flush(url)        

"""
Proceed to the injection process for the appropriate parameter.
"""
def injection_proccess(url, check_parameter, http_request_method, filename, delay):

  # User-Agent Injection / Referer Injection / Custom header Injection 
  if check_parameter.startswith(" "):
    header_name = ""
    the_type = " HTTP header "
  else:
    if settings.COOKIE_INJECTION: 
      header_name = " Cookie"
      the_type = " HTTP header "
      check_parameter = " '" + check_parameter + "'"
    else:
      header_name = ""
      the_type = " parameter "
      check_parameter = " '" + check_parameter + "'"

  # Load modules
  modules_handler.load_modules(url, http_request_method, filename)

  if not settings.LOAD_SESSION:  
    print settings.INFO_SIGN + "Setting the " + "(" + http_request_method + ")" + check_parameter + header_name + the_type + "for tests."

  # Estimating the response time (in seconds)
  delay, url_time_response = requests.estimate_response_time(url, http_request_method, delay)

  # Check if it is vulnerable to classic command injection technique.
  if not menu.options.tech or "c" in menu.options.tech:
    if cb_handler.exploitation(url, delay, filename, http_request_method) != False:
      settings.CLASSIC_STATE = True
  else:
    settings.CLASSIC_STATE = False

  # Check if it is vulnerable to eval-based code injection technique.
  if not menu.options.tech or "e" in menu.options.tech:
    if eb_handler.exploitation(url, delay, filename, http_request_method) != False:
      settings.EVAL_BASED_STATE = True
  else:
    settings.EVAL_BASED_STATE = False

  # Check if it is vulnerable to time-based blind command injection technique.
  if not menu.options.tech or "t" in menu.options.tech:
    if tb_handler.exploitation(url, delay, filename, http_request_method, url_time_response) != False:
      settings.TIME_BASED_STATE = True
  else:
    settings.TIME_BASED_STATE = False

  # Check if it is vulnerable to file-based semiblind command injection technique.
  if not menu.options.tech or "f" in menu.options.tech:
    if fb_handler.exploitation(url, delay, filename, http_request_method, url_time_response) != False:
      settings.FILE_BASED_STATE = True
  else:
    settings.FILE_BASED_STATE = False

  # All injection techniques seems to be failed!
  if settings.CLASSIC_STATE == settings.EVAL_BASED_STATE == settings.TIME_BASED_STATE == settings.FILE_BASED_STATE == False :
    info_msg = settings.WARNING_SIGN + "The tested (" + http_request_method + ")" + check_parameter + header_name + the_type + "seems to be not injectable."
    print Fore.YELLOW + info_msg + Style.RESET_ALL  

"""
Inject HTTP headers (User-agent / Referer) (if level > 2).
"""
def http_headers_injection(url, http_request_method, filename, delay):

  user_agent = menu.options.agent
  menu.options.agent = settings.INJECT_TAG
  settings.USER_AGENT_INJECTION = True
  if settings.USER_AGENT_INJECTION:
    check_parameter = header_name = " User-Agent"
    settings.HTTP_HEADER = header_name[1:].replace("-","").lower()
    injection_proccess(url, check_parameter, http_request_method, filename, delay)
    settings.USER_AGENT_INJECTION = False
    
  # Referer header injection
  menu.options.agent = user_agent
  menu.options.referer = settings.INJECT_TAG
  settings.REFERER_INJECTION = True
  if settings.REFERER_INJECTION:
    check_parameter =  header_name = " Referer"
    settings.HTTP_HEADER = header_name[1:].lower()
    injection_proccess(url, check_parameter, http_request_method, filename, delay)
    settings.REFERER_INJECTION = False 

"""
Check for stored injections on User-agent / Referer headers (if level > 2).
"""
def stored_http_header_injection(url, check_parameter, check_http_headers, http_request_method, filename, delay):

  for check_parameter in settings.HTTP_HEADERS:
    settings.HTTP_HEADER = check_parameter
    if check_for_stored_sessions(url, http_request_method):
      if check_parameter == "referer":
        menu.options.referer = settings.INJECT_TAG
        settings.REFERER_INJECTION = True
      else:  
        menu.options.agent = settings.INJECT_TAG
        settings.USER_AGENT_INJECTION = True
      injection_proccess(url, check_parameter, http_request_method, filename, delay)

  if not settings.LOAD_SESSION and check_http_headers == True:
    http_headers_injection(url, http_request_method, filename, delay)

"""
General check on every injection technique.
"""
def do_check(url, filename):

  check_http_headers = False

  # Check if defined "--delay" option.
  if menu.options.delay:
    delay = menu.options.delay
  else:
    delay = settings.DELAY

  # Check if authentication is needed.
  if menu.options.auth_url and menu.options.auth_data:
    # Do the authentication process.
    authentication.authentication_process()
    # Check if authentication page is the same with the next (injection) URL
    if urllib2.urlopen(url).read() == urllib2.urlopen(menu.options.auth_url).read():
      print Back.RED + settings.ERROR_SIGN + "It seems that the authentication procedure has failed." + Style.RESET_ALL
      sys.exit(0)
  elif menu.options.auth_url or menu.options.auth_data: 
    print Back.RED + settings.ERROR_SIGN + "You must specify both login panel URL and login parameters." + Style.RESET_ALL
    sys.exit(0)
  else:
    pass

  # Check if HTTP Method is GET.
  if not menu.options.data:

    # Enable Cookie Injection
    if menu.options.cookie and menu.options.level > 1:
      settings.COOKIE_INJECTION = True

    http_request_method = "GET"

    # Check for stored injections on User-agent / Referer headers (if level > 2).
    if menu.options.level > 2 :
      check_parameter = ""
      stored_http_header_injection(url, check_parameter, check_http_headers, http_request_method, filename, delay)

    # Enable Cookie Injection
    if menu.options.cookie:
      settings.COOKIE_INJECTION = True

    if not settings.COOKIE_INJECTION:
      found_url = parameters.do_GET_check(url)
      if found_url != False:
        for i in range(0, len(found_url)):
          url = found_url[i]
          check_parameter = parameters.vuln_GET_param(url)
          # Check if testable parameter(s) are provided
          if len(settings.TEST_PARAMETER) > 0:
            if check_parameter in settings.TEST_PARAMETER:
              # Check for session file 
              if check_for_stored_sessions(url, http_request_method):
                injection_proccess(url, check_parameter, http_request_method, filename, delay)
          else:
            if check_for_stored_sessions(url, http_request_method):
              injection_proccess(url, check_parameter, http_request_method, filename, delay)

        if not settings.LOAD_SESSION :
          for i in range(0, len(found_url)):
            url = found_url[i]
            check_parameter = parameters.vuln_GET_param(url)
            # Check if testable parameter(s) are provided
            if len(settings.TEST_PARAMETER) > 0:
              if check_parameter in settings.TEST_PARAMETER:
                injection_proccess(url, check_parameter, http_request_method, filename, delay)
            else:
              injection_proccess(url, check_parameter, http_request_method, filename, delay)

  # Check if HTTP Method is POST.      
  else:
    http_request_method = "POST"
    
    # Check for stored injections on User-agent / Referer headers (if level > 2).
    if menu.options.level > 2 :
      check_parameter = ""
      stored_http_header_injection(url, check_parameter, check_http_headers, http_request_method, filename, delay)

    # Check if HTTP Method is POST.
    parameter = menu.options.data
    found_parameter = parameters.do_POST_check(parameter)
    # Remove whitespaces 
    # Check if singe entry parameter
    if type(found_parameter) is str:
      found_parameter_list = []
      found_parameter_list.append(found_parameter)
      found_parameter = found_parameter_list

    # Remove whitespaces   
    found_parameter = [x.replace(" ", "") for x in found_parameter]

    # Check if multiple parameters
    for i in range(0, len(found_parameter)):
      parameter = menu.options.data = found_parameter[i]
      check_parameter = parameters.vuln_POST_param(parameter, url)
      if len(check_parameter) > 0:
        settings.TESTABLE_PARAMETER = check_parameter
      # Check if testable parameter(s) are provided
      if len(settings.TEST_PARAMETER) > 0:
        if check_parameter in settings.TEST_PARAMETER:
          # Check for session file 
          if check_for_stored_sessions(url, http_request_method):
            injection_proccess(url, check_parameter, http_request_method, filename, delay)
      else:
        if check_for_stored_sessions(url, http_request_method):
          injection_proccess(url, check_parameter, http_request_method, filename, delay)

    if not settings.LOAD_SESSION :
      for i in range(0, len(found_parameter)):
        parameter = menu.options.data = found_parameter[i]
        check_parameter =  parameters.vuln_POST_param(parameter, url)
        # Check if testable parameter(s) are provided
        if len(settings.TEST_PARAMETER) > 0:
          if check_parameter in settings.TEST_PARAMETER:
            injection_proccess(url, check_parameter, http_request_method, filename, delay)
        else:
          injection_proccess(url, check_parameter, http_request_method, filename, delay)  

  # Enable Cookie Injection
  if menu.options.cookie and menu.options.level > 1:
    settings.COOKIE_INJECTION = True

  # Cookie Injection
  if settings.COOKIE_INJECTION == True:
    cookie_value = menu.options.cookie
    # Check for stored injections on User-agent / Referer headers (if level > 2).
    if menu.options.level > 2 :
      check_parameter = ""
      stored_http_header_injection(url, check_parameter, check_http_headers, http_request_method, filename, delay)

    header_name = " Cookie"
    settings.HTTP_HEADER = header_name[1:].lower()
    cookie_parameters = parameters.do_cookie_check(menu.options.cookie)
    if type(cookie_parameters) is str:
      cookie_parameters_list = []
      cookie_parameters_list.append(cookie_parameters)
      cookie_parameters = cookie_parameters_list

    # Remove whitespaces 
    cookie_parameters = [x.replace(" ", "") for x in cookie_parameters]

    for i in range(0, len(cookie_parameters)):
      menu.options.cookie = cookie_parameters[i]
      check_parameter = parameters.specify_cookie_parameter(menu.options.cookie)
      if len(check_parameter) > 0:
        settings.TESTABLE_PARAMETER = check_parameter 
      # Check if testable parameter(s) are provided
      if len(settings.TEST_PARAMETER) > 0:
        if check_parameter in settings.TEST_PARAMETER:
          # Check for session file 
          if check_for_stored_sessions(url, http_request_method):
            injection_proccess(url, check_parameter, http_request_method, filename, delay)
      else:
        if check_for_stored_sessions(url, http_request_method):
          injection_proccess(url, check_parameter, http_request_method, filename, delay)

    if not settings.LOAD_SESSION :
      for i in range(0, len(cookie_parameters)):
        menu.options.cookie = cookie_parameters[i]
        check_parameter = parameters.specify_cookie_parameter(menu.options.cookie)
        if len(check_parameter) > 0:
          settings.TESTABLE_PARAMETER = check_parameter 
        # Check if testable parameter(s) are provided
        if len(settings.TEST_PARAMETER) > 0:
          if check_parameter in settings.TEST_PARAMETER:
            injection_proccess(url, check_parameter, http_request_method, filename, delay)
        else:
          injection_proccess(url, check_parameter, http_request_method, filename, delay)
  
  if settings.COOKIE_INJECTION == True:
    # Restore cookie value
    menu.options.cookie = cookie_value
    # Disable cookie injection 
    settings.COOKIE_INJECTION = False

  # Custom header Injection
  if settings.CUSTOM_HEADER_INJECTION == True:
    check_parameter =  header_name = " " + settings.CUSTOM_HEADER_NAME
    settings.HTTP_HEADER = header_name[1:].lower()
    check_for_stored_sessions(url, http_request_method)
    injection_proccess(url, check_parameter, http_request_method, filename, delay)

  # Check for stored injections on User-agent / Referer headers (if level > 2).
  if menu.options.level > 2 :
    check_parameter = ""
    check_http_headers = True
    stored_http_header_injection(url, check_parameter, check_http_headers, http_request_method, filename, delay)

  # All injection techniques seems to be failed!
  if settings.CLASSIC_STATE == settings.EVAL_BASED_STATE == settings.TIME_BASED_STATE == settings.FILE_BASED_STATE == False :
    info_msg = settings.CRITICAL_SIGN + "All the tested (" + http_request_method + ") parameters appear to be not injectable."
    if not menu.options.alter_shell :
      info_msg += " Try to use the option '--alter-shell'"
    else:
      info_msg += " Try to remove the option '--alter-shell'"
    if menu.options.level < 3 :
      info_msg += " and/or try to increase '--level' values to perform more tests (i.e 'User-Agent', 'Referer', 'Cookie' etc)"
    info_msg += "."
    print Back.RED + info_msg + Style.RESET_ALL  
  sys.exit(0)

#eof
#!/usr/bin/env python

# 
# exec-by-mail
#
# Copyright (C) 2014 Mikhail Fedotov <anyremote@mail.ru>
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA. 
# 

import getopt
import commands
import imaplib
import re
import socket
import smtplib
import email.Header
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText
from email import Encoders
import sys, os, time, atexit
from signal import SIGTERM

################################################################################
#
#  A generic daemon class
#
################################################################################
class Daemon:
  """
  A generic daemon class.

  Usage: subclass the Daemon class and override the run() method
  """
  def __init__(self, pidfile, stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
    self.stdin = stdin
    self.stdout = stdout
    self.stderr = stderr
    self.pidfile = pidfile

  def daemonize(self):
    """
    do the UNIX double-fork magic, see Stevens' "Advanced
    Programming in the UNIX Environment" for details (ISBN 0201563177)
    http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
    """
    try:
      pid = os.fork()
      if pid > 0:
        # exit first parent
        sys.exit(0)
    except OSError, e:
      sys.stderr.write("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
      sys.exit(1)

    # decouple from parent environment
    os.chdir("/")
    os.setsid()
    os.umask(0)

    # do second fork
    try:
      pid = os.fork()
      if pid > 0:
        # exit from second parent
        sys.exit(0)
    except OSError, e:
      sys.stderr.write("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
      sys.exit(1)

    # redirect standard file descriptors
    sys.stdout.flush()
    sys.stderr.flush()
    si = file(self.stdin, 'r')
    so = file(self.stdout, 'a+')
    se = file(self.stderr, 'a+', 0)
    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())
    
    # write pidfile
    try:
      pid = str(os.getpid())
      self.pidnum = pid
      file(self.pidfile,'w+').write("%s\n" % pid)

      atexit.register(self.delpid)
    except IOError, e:
      pass

  def delpid(self):
    try:
      os.remove(self.pidfile)
    except OSError, e:
      pass

  def start(self):
    """
    Start the daemon
    """
    # Check for a pidfile to see if the daemon already runs
    try:
      pf = file(self.pidfile,'r')
      pid = int(pf.read().strip())
      pf.close()
    except IOError:
      pid = None

    if pid:
      message = "pidfile %s already exist. Daemon already running?\n"
      sys.stderr.write(message % self.pidfile)
      sys.exit(1)

    # Start the daemon
    self.daemonize()
    self.run()

  def stop(self):
    """
    Stop the daemon
    """
    # Get the pid from the pidfile
    try:
      pf = file(self.pidfile,'r')
      pid = int(pf.read().strip())
      pf.close()
    except IOError:
      pid = None

    if not pid:
      message = "pidfile %s does not exist. Daemon not running?\n"
      sys.stderr.write(message % self.pidfile)
      return # not an error in a restart

    # Try killing the daemon process
    try:
      while 1:
        os.kill(pid, SIGTERM)
        time.sleep(0.1)
    except OSError, err:
      err = str(err)
      if err.find("No such process") > 0:
        if os.path.exists(self.pidfile):
          try:
            os.remove(self.pidfile)
          except OSError, e:
            pass
      else:
        print str(err)
        sys.exit(1)

  def restart(self):
    """
    Restart the daemon
    """
    self.stop()
    self.start()

  def run(self):
    """
    You should override this method when you subclass Daemon. It will be called after the process has been
    daemonized by start() or restart().
    """

################################################################################
#
#  mail2cmd daemon class
#
################################################################################
class Mail2CmdDaemon(Daemon):

  def run(self):
    while True:
      self.process()
      try:
        tm = _timeout
      except NameError:
        tm = 30
      time.sleep(tm)


  def process(self):
    try:
      mail = imaplib.IMAP4_SSL(_imapserver)
      mail.login(_imaplogin, _imappass)
      mail.select("inbox")
      
      typ, data = mail.search(None, 'ALL')
      
      #print typ, data
      for num in data[0].split():
        self.processOneMail(mail, num)
      
      mail.close()
      mail.logout()
      
    except imaplib.IMAP4.error, msg:
      pass
    except socket.error:
      pass


  def processOneMail(self, mail, num):
    try:
      typ, data = mail.fetch(num, '(BODY.PEEK[])')
      print typ, data
      raw_mail = data[0][1]
      mailMsg = email.message_from_string(raw_mail)
      mFrom = email.Header.decode_header(mailMsg['From'])
      
      if len(mFrom) == 1:
        mailFrom = mFrom[0][0]
        matchObj = re.search( r'.*<(.*)>.*', mailFrom)
        if matchObj:
          mailFrom = matchObj.group(1)
      else:
        mailFrom = mFrom[1][0]
        mailFrom = mailFrom[1:-1]

      if self.isAllowed(mailFrom):
        try:
          reply = email.Header.decode_header(mailMsg['Reply-To'])
          replyTo = reply[1][0]
          replyTo = replyTo[1:-1]
        except IndexError:
          replyTo = mailFrom
       
        try:
          subject = email.Header.decode_header(mailMsg['Subject'])
          #print "subjA ", subject
          subject = subject[0][0]
          #print "subjB ", subject
        except IndexError:
          subject = ""
         
        if mailMsg.get_content_maintype() == 'multipart':
          for part in mailMsg.walk():
            if part.get_content_type() == "text/plain":
              body = part.get_payload(decode=True)
              self.processBody(body, replyTo, subject, mailFrom)
        else:
          if mailMsg.get_content_type() == "text/plain":
            body = mailMsg.get_payload(decode=True)
            self.processBody(body, replyTo, subject, mailFrom)
          
      else:
        pass
	#print "processing denyed"
    except IndexError:
      #print "IndexError"
      pass
    mail.store(num, '+FLAGS', '\\Deleted')

 
  def processBody(self, body, replyTo, subject, mailFrom):
    cmdList = body.split('\n')
    for cmd in cmdList:
      self.handleCommand(cmd.lstrip(), replyTo, subject, mailFrom)


  def isAllowed(self, mailFrom):
    ret = False
    try:
      if _allow:
        for item in _allow:
          if item[0] == '@':
            if mailFrom.endswith(item):
              ret = True
              break
          else:
            if mailFrom == item:
              ret = True
              break
      else:
        ret = True
    except NameError:
      ret = True
      
    if not ret:
      return False
      
    try:
      if _deny:
        for item in _deny:
          if item[0] == '@':
            if mailFrom.endswith(item):
              return False
          else:
            if mailFrom == item:
              return False
    except NameError:
      pass
    return True


  def handleCommand(self, cmd, replyTo, subject, mailFrom):
    if cmd:
      #print 'Command:',cmd
      cmdList = cmd.split()
      for handler in _config:
        if cmdList[0] == handler[0]:
          self.handle(handler, replyTo, cmdList, subject, mailFrom)
          break
 

  def handle(self, handler, replyTo, cmdList, subject, mailFrom):
    if len(cmdList) == 1 or cmdList[1] == "":
      self.handleSub(handler[1], replyTo, cmdList, subject, mailFrom)
    else:
      for sub in handler[1:]:
        if sub[0] == cmdList[1]:
          self.handleSub(sub, replyTo, cmdList, subject, mailFrom)
          break


  def substParams(self, param, cmdList, mailFrom):
    if param != "":
      for i in range(1,9):
        template = "%"+str(i)
        if param.find(template) >= 0 and len(cmdList) > i + 1:
          param = param.replace(template, cmdList[i + 1])
      if param.find("%f") >= 0 and mailFrom:
        param = param.replace("%f", mailFrom)
    return param


  def handleSub(self, cmdDefinition, replyTo, cmdList, subject, mailFrom):
   
    print cmdDefinition
    
    script = cmdDefinition[1]
    
    replyB = (cmdDefinition[2] == "Body"       or cmdDefinition[2] == "B" or cmdDefinition[2] == "True")
    replyA = (cmdDefinition[2] == "Attachment" or cmdDefinition[2] == "A")
    replyF = (cmdDefinition[2] == "File"       or cmdDefinition[2] == "F")

    header = self.substParams(cmdDefinition[3], cmdList, mailFrom)

    data = ""
    if script != "":
      script = self.substParams(script, cmdList, mailFrom)
      if replyA or replyB:
        data = self.getResult(script)
      elif replyF:
        data = script
      else:
        #print 'SCRIPT ',script
        if script:
          os.system(script)
        
    if not (replyA or replyB or replyF):
      return
    
    if replyA or replyF:
      msg = MIMEMultipart()
      msg.attach(MIMEText(header))
      
      part = MIMEBase('application', "octet-stream")
      if replyA:
         part.set_payload(data)
         Encoders.encode_base64(part)
         part.add_header('Content-Disposition', 'attachment; filename="file.tmp"')
         msg.attach(part)
      elif replyF:
         try:
           part.set_payload(open(data,"rb").read())
           Encoders.encode_base64(part)
           part.add_header('Content-Disposition', 'attachment; filename="%s"' % os.path.basename(data))
           msg.attach(part)
         except:
           pass
    else:
      msg = MIMEText(header+"\n"+data)
    self.reply(replyTo, msg, subject)


  def reply(self, replyTo, msg, subject):
    msg['Subject'] = 'Re: %s' % subject
    msg['From']    = _smtplogin
    msg['To']      = replyTo
    server = smtplib.SMTP(_smtpserver)
    #server.set_debuglevel(1)
    server.starttls()
    try:
      server.login(_smtplogin, _smtppass)
      server.sendmail(_smtplogin, [replyTo], msg.as_string())
    except SMTPException:
      pass
    print 'SEND REPLAY'
    server.quit()
    print 'SEND REPLAY OK'


  def getResult(self, cmd):
    if cmd:
      queryresult = commands.getstatusoutput(cmd)
      strData = "\n".join(str(item) for item in queryresult)
    else:
      strData = ""
    return strData


def usage():
  print "usage: %s --start|--stop|--restart -f config_file" % sys.argv[0]


if __name__ == "__main__":
    try:
      opts, args = getopt.getopt(sys.argv[1:], "f:", ["start", "stop", "restart", "f="])
    except getopt.GetoptError:
      usage()
      sys.exit(2)

    config=""
    for o, a in opts:
      if o in ("-f"):
        config = a
    
    if config == "" :
      usage()
      sys.exit(2)
    
    execfile(config)
    
    try:
      pidfile = _pidfile
    except NameError:
      pidfile = '/var/run/exec-by-mail.pid'

    daemon = Mail2CmdDaemon(pidfile)

    for o, a in opts:
      
      if o in ("--start"):
        daemon.start()
      
      elif o in ("--stop"):
        daemon.stop()
      
      elif o in ("--restart"):
        daemon.stop()
        daemon.start()
      
      else:
         print "Unknown command"
         sys.exit(2)

      sys.exit(0)

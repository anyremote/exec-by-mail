# 
# exec-by-mail
#
# Copyright (C) 2015 Mikhail Fedotov <anyremote@mail.ru>
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

EXTRA_DIST = exec-by-mail exec-by-mail.conf

dist_bin_SCRIPTS = exec-by-mail.py

ACLOCAL_AMFLAGS = -I m4

install-data-local:
	cp -r exec-by-mail /etc/init.d/
	cp -r exec-by-mail.conf /etc/exec-by-mail.conf.example
	chmod +x /etc/init.d/exec-by-mail /usr/bin/exec-by-mail.py
	ln -s /etc/init.d/exec-by-mail /etc/rc0.d/K97exec-by-mail
	ln -s /etc/init.d/exec-by-mail /etc/rc1.d/K97exec-by-mail
	ln -s /etc/init.d/exec-by-mail /etc/rc6.d/K97exec-by-mail
	ln -s /etc/init.d/exec-by-mail /etc/rc2.d/S97exec-by-mail
	ln -s /etc/init.d/exec-by-mail /etc/rc3.d/S97exec-by-mail
	ln -s /etc/init.d/exec-by-mail /etc/rc4.d/S97exec-by-mail
	ln -s /etc/init.d/exec-by-mail /etc/rc5.d/S97exec-by-mail
	
uninstall-local:
	rm -f /etc/init.d/exec-by-mail /etc/exec-by-mail.conf.example
	rm -f /etc/rc0.d/K97exec-by-mail
	rm -f /etc/rc1.d/K97exec-by-mail
	rm -f /etc/rc6.d/K97exec-by-mail
	rm -f /etc/rc2.d/S97exec-by-mail
	rm -f /etc/rc3.d/S97exec-by-mail
	rm -f /etc/rc4.d/S97exec-by-mail
	rm -f /etc/rc5.d/S97exec-by-mail


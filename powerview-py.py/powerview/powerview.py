#!/usr/bin/env python3
from impacket.examples.ntlmrelayx.utils.config import NTLMRelayxConfig
from impacket.dcerpc.v5 import srvs, wkst, scmr, rrp
from impacket.dcerpc.v5.ndr import NULL
from impacket.crypto import encryptSecret
from typing import List

from powerview.modules.gmsa import GMSA
from powerview.modules.ca import CAEnum, PARSE_TEMPLATE, UTILS
from powerview.modules.sccm import SCCM
from powerview.modules.addcomputer import ADDCOMPUTER
from powerview.modules.smbclient import SMBClient
from powerview.modules.kerberoast import GetUserSPNs
from powerview.modules.dacledit import DACLedit
from powerview.modules.products import EDR
from powerview.modules.gpo import GPO
from powerview.utils.helpers import *
from powerview.utils.connections import CONNECTION
from powerview.utils.storage import Storage
from powerview.modules.ldapattack import (
	LDAPAttack,
	ACLEnum,
	ADUser,
	ObjectOwner,
	RBCD
)
from powerview.utils.colors import bcolors
from powerview.utils.constants import (
	WELL_KNOWN_SIDS,
	KNOWN_SIDS,
	resolve_WellKnownSID,
	SERVICE_TYPE,
	SERVICE_START_TYPE,
	SERVICE_ERROR_CONTROL,
	SERVICE_STATUS,
	SERVICE_WIN32_EXIT_CODE
)
from powerview.lib.dns import (
	DNS_RECORD,
	DNS_RPC_RECORD_A,
	DNS_UTIL,
)
from powerview.lib.reg import RemoteOperations
from powerview.lib.samr import SamrObject
from powerview.lib.resolver import (
	UAC,
	LDAP
)
from powerview.lib.ldap3.extend import CustomExtendedOperationsRoot
from powerview.web.api.server import APIServer

import chardet
import time
from io import BytesIO
import ldap3
from ldap3.protocol.microsoft import security_descriptor_control
from ldap3.extend.microsoft import addMembersToGroups, modifyPassword, removeMembersFromGroups
from ldap3.utils.conv import escape_filter_chars
import re
import inspect

class PowerView:
	def __init__(self, conn, args, target_server=None, target_domain=None):
		self.conn = conn
		self.args = args
		
		self.ldap_server, self.ldap_session = self.conn.init_ldap_session()

		self.custom_paged_search = CustomExtendedOperationsRoot(self.ldap_session, obfuscate=self.args.obfuscate, no_cache=self.args.no_cache)
		self.ldap_session.extend.standard.paged_search = self.custom_paged_search.standard.paged_search

		self.username = args.username if args.username else self.conn.get_username()
		self.password = args.password

		self.lmhash = args.lmhash
		self.nthash = args.nthash
		self.auth_aes_key = args.auth_aes_key
		self.use_ldaps = args.use_ldaps
		self.nameserver = args.nameserver
		self.use_system_nameserver = args.use_system_ns
		self.dc_ip = args.dc_ip
		self.use_kerberos = args.use_kerberos

		if target_domain:
			self.domain = target_domain
		else:
			self.domain = conn.get_domain()

		self.use_ldaps = self.ldap_session.server.ssl

		cnf = ldapdomaindump.domainDumpConfig()
		cnf.basepath = None
		self.domain_dumper = ldapdomaindump.domainDumper(self.ldap_server, self.ldap_session, cnf)
		self.root_dn = self.ldap_server.info.other["defaultNamingContext"][0]
		if not self.domain:
			self.domain = dn2domain(self.root_dn)
		self.flatName = self.ldap_server.info.other["ldapServiceName"][0].split("@")[-1].split(".")[0]
		self.dc_dnshostname = self.ldap_server.info.other["dnsHostName"][0] if isinstance(self.ldap_server.info.other["dnsHostName"], list) else self.ldap_server.info.other["dnsHostName"]
		if not target_domain:
			self.is_admin = self.is_admin()

		# API server
		if self.args.web and self.ldap_session:
			try:
				from powerview.web.api.server import APIServer
				self.api_server = APIServer(self, host=self.args.web_host, port=self.args.web_port)
				self.api_server.start()
			except ImportError:
				logging.warning("Web interface dependencies not installed. Web interface will not be available.")

		# Get current user's SID from the LDAP connection
		self.current_user_sid = None
		self.whoami = self.conn.who_am_i()
		if self.whoami and self.whoami != 'ANONYMOUS':
			user = self.get_domainobject(identity=self.whoami.split('\\')[1], properties=['objectSid'])
			if user and len(user) > 0:
				self.current_user_sid = user[0]['attributes']['objectSid']

	def get_admin_status(self):
		return self.is_admin

	def is_connection_alive(self):
		try:
			self.ldap_session.search(search_base='', search_filter='(objectClass=*)', search_scope='BASE', attributes=['namingContexts'])
			return self.ldap_session.result['result'] == 0
		except Exception as e:
			print(f"Connection is not alive: {e}")
			return False

	def get_server_dns(self):
		return self.dc_dnshostname

	def execute(self, args):
		module_name = args.module
		method_name = module_name.replace('-', '_').lower()
		method = getattr(self, method_name, None)
		if not method:
			raise ValueError(f"Method {method_name} not found in PowerView")
		# Get the method's signature
		method_signature = inspect.signature(method)
		method_params = method_signature.parameters
		# Filter out unsupported arguments
		method_args = {k: v for k, v in vars(args).items() if k in method_params}
		return method(**method_args)

	def is_admin(self):
		self.is_domainadmin = False
		self.is_admincount = False
		groups = []

		try:
			curUserDetails = self.get_domainobject(identity=self.username, properties=["adminCount","memberOf"])[0]
		   
			if not curUserDetails:
				return False
			
			userGroup = curUserDetails.get("attributes").get("memberOf")

			if isinstance(userGroup, str):
				groups.append(userGroup)
			elif isinstance(userGroup, list):
				groups = userGroup 

			for group in groups:
				if "CN=Domain Admins".casefold() in group.casefold():
					self.is_domainadmin = True
					break

			if self.is_domainadmin:
				logging.info(f"User {self.username} is a Domain Admin")
			else:
				self.is_admincount = bool(curUserDetails["attributes"]["adminCount"])
				if self.is_admincount:
					logging.info(f"User {self.username} has adminCount attribute set to 1. Might be admin somewhere somehow :)")
		except:
			if self.args.stack_trace:
				raise
			else:
				logging.debug("Failed to check user admin status")

		return self.is_domainadmin or self.is_admincount

	def clear_cache(self) -> bool:
		logging.info("[Clear-Cache] Clearing cache")
		return self.custom_paged_search.standard.storage.clear_cache()

	def get_domainuser(self, args=None, properties=[], identity=None, searchbase=None, search_scope=ldap3.SUBTREE, no_cache=False):
		def_prop = [
			'servicePrincipalName', 'objectCategory', 'objectGUID', 'primaryGroupID', 'userAccountControl',
			'sAMAccountType', 'adminCount', 'cn', 'name', 'sAMAccountName', 'distinguishedName', 'mail',
			'description', 'lastLogoff', 'lastLogon', 'memberOf', 'objectSid', 'userPrincipalName', 
			'pwdLastSet', 'badPwdCount', 'badPasswordTime', 'msDS-SupportedEncryptionTypes'
		]
		
		if args and hasattr(args, 'properties') and args.properties:
			properties = set(args.properties)
		else:
			properties = set(properties or def_prop)

		no_cache = args.no_cache if hasattr(args, 'no_cache') and args.no_cache else no_cache
		
		if not searchbase:
			searchbase = args.searchbase if hasattr(args, 'searchbase') and args.searchbase else self.root_dn 

		logging.debug(f"[Get-DomainUser] Using search base: {searchbase}")

		ldap_filter = ""
		identity_filter = ""

		if identity:
			identity_filter += f"(|(sAMAccountName={identity})(distinguishedName={identity}))"
		elif args and hasattr(args, 'identity') and args.identity:
			identity_filter += f"(|(sAMAccountName={args.identity})(distinguishedName={args.identity}))"

		if args:
			if hasattr(args, 'preauthnotrequired') and args.preauthnotrequired:
				logging.debug("[Get-DomainUser] Searching for user accounts that do not require kerberos preauthenticate")
				ldap_filter += f'(userAccountControl:1.2.840.113556.1.4.803:=4194304)'
			if hasattr(args, 'passnotrequired') and args.passnotrequired:
				logging.debug("[Get-DomainUser] Searching for user accounts that have PASSWD_NOTREQD set")
				ldap_filter += f'(userAccountControl:1.2.840.113556.1.4.803:=32)'
			if hasattr(args, 'admincount') and args.admincount:
				logging.debug('[Get-DomainUser] Searching for adminCount=1')
				ldap_filter += f'(admincount=1)'
			if hasattr(args, 'lockout') and args.lockout:
				logging.debug('[Get-DomainUser] Searching for locked out user')
				ldap_filter += f'(userAccountControl:1.2.840.113556.1.4.803:=16)'
			if hasattr(args, 'allowdelegation') and args.allowdelegation:
				logging.debug('[Get-DomainUser] Searching for users who can be delegated')
				ldap_filter += f'(!(userAccountControl:1.2.840.113556.1.4.803:=1048574))'
			if hasattr(args, 'disallowdelegation') and args.disallowdelegation:	
				logging.debug('[Get-DomainUser] Searching for users who are sensitive and not trusted for delegation')
				ldap_filter += f'(userAccountControl:1.2.840.113556.1.4.803:=1048576)'
			if hasattr(args, 'trustedtoauth') and args.trustedtoauth:
				logging.debug('[Get-DomainUser] Searching for users that are trusted to authenticate for other principals')
				ldap_filter += f'(userAccountControl:1.2.840.113556.1.4.803:=16777216)'
				properties.add('msds-AllowedToDelegateTo')
			if hasattr(args, 'rbcd') and args.rbcd:
				logging.debug('[Get-DomainUser] Searching for users that are configured to allow resource-based constrained delegation')
				ldap_filter += f'(msds-allowedtoactonbehalfofotheridentity=*)'
			if hasattr(args, 'shadowcred') and args.shadowcred:
				logging.debug("[Get-DomainUser] Searching for users that are configured to have msDS-KeyCredentialLink attribute set")
				ldap_filter += f'(msDS-KeyCredentialLink=*)'
				properties.add('msDS-KeyCredentialLink')
			if hasattr(args, 'spn') and args.spn:
				logging.debug("[Get-DomainUser] Searching for users that have SPN attribute set")
				ldap_filter += f'(&(servicePrincipalName=*)(!(name=krbtgt)))'
			if hasattr(args, 'unconstrained') and args.unconstrained:
				logging.debug("[Get-DomainUser] Searching for users configured for unconstrained delegation")
				ldap_filter += f'(userAccountControl:1.2.840.113556.1.4.803:=524288)'
			if hasattr(args, 'enabled') and args.enabled:
				logging.debug("[Get-DomainUser] Searching for enabled user")
				ldap_filter += f'(!(userAccountControl:1.2.840.113556.1.4.803:=2))'
			if hasattr(args, 'disabled') and args.disabled:
				logging.debug("[Get-DomainUser] Searching for disabled user")
				ldap_filter += f'(userAccountControl:1.2.840.113556.1.4.803:=2)'
			if hasattr(args, 'password_expired') and args.password_expired:
				logging.debug("[Get-DomainUser] Searching for user with expired password")
				ldap_filter += f'(userAccountControl:1.2.840.113556.1.4.803:=8388608)'
			if hasattr(args, 'ldapfilter') and args.ldapfilter:
				logging.debug(f'[Get-DomainUser] Using additional LDAP filter: {args.ldapfilter}')
				ldap_filter += f'{args.ldapfilter}'

		# previous ldap filter, need to changed to filter based on objectClass instead because i couldn't get the trust account
		#ldap_filter = f'(&(samAccountType=805306368){identity_filter}{ldap_filter})'
		ldap_filter = f'(&(objectCategory=person)(objectClass=user){identity_filter}{ldap_filter})'

		logging.debug(f'[Get-DomainUser] LDAP search filter: {ldap_filter}')

		# in case need more then 1000 entries
		entries = []
		entry_generator = self.ldap_session.extend.standard.paged_search(searchbase,ldap_filter,attributes=list(properties), paged_size = 1000, generator=True, search_scope=search_scope, no_cache=no_cache)
		for _entries in entry_generator:
			if _entries['type'] != 'searchResEntry':
				continue
			strip_entry(_entries)
			entries.append(_entries)
		return entries

	def get_localuser(self, computer_name, identity=None, properties=[], port=445, args=None):
		entries = list()

		if computer_name is None:
			#computer_name = host2ip(self.get_server_dns(), self.nameserver, 3, True, use_system_ns=self.use_system_nameserver, type=list)
			computer_name = self.get_server_dns()

		default_properties = {'username', 'userrid', 'fullname', 'homedirectory', 'allowedworkstation', 
						  'comment', 'accountactive', 'passwordlastset', 'passwordexpires', 
						  'lastlogon', 'logoncount', 'localgroupmemberships', 'globalgroupmemberships'}
	
		properties = set(prop.lower() for prop in (properties or default_properties))

		invalid_properties = properties - default_properties
		if invalid_properties:
			logging.error(f"[Get-LocalUser] Invalid properties: {', '.join(invalid_properties)}")
			return

		if is_ipaddress(computer_name) and self.use_kerberos:
			logging.error("[Get-NetLoggedOn] Use FQDN when using kerberos")
			return

		samrobj = SamrObject(
			connection = self.conn,
			port = port
		)

		dce = samrobj.connect(computer_name)
		samrh = samrobj.open_handle(dce)

		rids = list()
		if identity:
			rid = samrobj.get_object_rid(dce, samrh, identity)
			if rid is None:
				return
			rids.append(rid)
		else:
			users = samrobj.get_all_local_users(dce, samrh)
			rids = [user['RelativeId'] for user in users]

		if not rids:
			logging.error("No RIDs found. Skipping...")
			return

		logging.debug("[Get-LocalAccount] Found RIDs {}".format(rids))


		for rid in rids:
			entry = dict({
				"attributes": dict()
			})
			samrh = samrobj.open_handle(dce)
			user_info = samrobj.get_local_user(dce, samrh, rid)

			if 'username' in properties:
				entry['attributes']['userName'] = user_info['UserName']
			if 'userrid' in properties:
				entry['attributes']['userRID'] = rid
			if 'fullname' in properties:
				entry['attributes']['fullName'] = user_info['FullName']
			if 'homedirectory' in properties:
				entry['attributes']['homeDirectory'] = user_info['HomeDirectory']
			if 'allowedworkstation' in properties:
				entry['attributes']['allowedWorkstation'] = "All" if not user_info['WorkStations'] else user_info['WorkStations']
			if 'comment' in properties:
				entry['attributes']['comment'] = user_info['AdminComment']
			if 'accountactive' in properties:
				entry['attributes']['accountActive'] = user_info['UserAccountControl'] & samr.USER_ACCOUNT_DISABLED != samr.USER_ACCOUNT_DISABLED
			if 'passwordlastset' in properties:
				entry['attributes']['passwordLastSet'] = get_time_string(user_info['PasswordLastSet'])
			if 'passwordexpires' in properties:
				entry['attributes']['passwordExpires'] = get_time_string(user_info['PasswordMustChange'])
			if 'lastlogon' in properties:
				entry['attributes']['lastLogon'] = get_time_string(user_info['LastLogon'])
			if 'logoncount' in properties:
				entry['attributes']['logonCount'] = user_info['LogonCount']
			if 'localgroupmemberships' in properties:
				entry['attributes']['localGroupMemberships'] = user_info['LocalGroups']
			if 'globalgroupmemberships' in properties:
				entry['attributes']['globalGroupMemberships'] = user_info['GlobalGroups']

			entries.append(entry)
		return entries

	def get_domaincontroller(self, args=None, properties=[], identity=None, searchbase=None, search_scope=ldap3.SUBTREE, no_cache=False):
		def_prop = [
			'cn',
			'distinguishedName',
			'instanceType',
			'whenCreated',
			'whenChanged',
			'name',
			'objectGUID',
			'userAccountControl',
			'badPwdCount',
			'badPasswordTime',
			'objectSid',
			'logonCount',
			'sAMAccountType',
			'sAMAccountName',
			'operatingSystem',
			'dNSHostName',
			'objectCategory',
			'msDS-SupportedEncryptionTypes',
			'msDS-AllowedToActOnBehalfOfOtherIdentity'
		]

		ldap_filter = ""
		identity_filter = ""

		no_cache = args.no_cache if hasattr(args, 'no_cache') and args.no_cache else no_cache
		properties = def_prop if not properties else properties
		if not searchbase:
			searchbase = args.searchbase if hasattr(args, 'searchbase') and args.searchbase else self.root_dn 
		
		logging.debug(f"[Get-DomainController] Using search base: {searchbase}")

		if identity:
			identity_filter += f"(|(name={identity})(sAMAccountName={identity})(dnsHostName={identity}))"

		if args:
			if args.ldapfilter:
				logging.debug(f'[Get-DomainController] Using additional LDAP filter: {args.ldapfilter}')
				ldap_filter += args.ldapfilter

		ldap_filter = f"(&(userAccountControl:1.2.840.113556.1.4.803:=8192){identity_filter}{ldap_filter})"
		logging.debug(f"[Get-DomainController] LDAP search filter: {ldap_filter}")
		entries = []
		entry_generator = self.ldap_session.extend.standard.paged_search(searchbase,ldap_filter,attributes=properties, paged_size = 1000, generator=True, search_scope=search_scope, no_cache=no_cache)
		for _entries in entry_generator:
			if _entries['type'] != 'searchResEntry':
				continue
			strip_entry(_entries)
			# resolve msDS-AllowedToActOnBehalfOfOtherIdentity
			try:
				if "msDS-AllowedToActOnBehalfOfOtherIdentity" in list(_entries["attributes"].keys()):
					parser = RBCD(_entries)
					sids = parser.read()
					if args.resolvesids:
						for i in range(len(sids)):
							sids[i] = self.convertfrom_sid(sids[i])
					_entries["attributes"]["msDS-AllowedToActOnBehalfOfOtherIdentity"] = sids
			except:
				pass

			entries.append(_entries)

		return entries

	def get_domainobject(self, args=None, properties=[], identity=None, identity_filter=None, ldap_filter=None, searchbase=None, sd_flag=None, search_scope=ldap3.SUBTREE, no_cache=False):
		def_prop = [
			'*'
		]
		properties = set(properties or def_prop)
		no_cache = args.no_cache if hasattr(args, 'no_cache') and args.no_cache else no_cache

		if sd_flag:
			controls = security_descriptor_control(sdflags=sd_flag)
		else:
			controls = None

		identity_filter = "" if not identity_filter else identity_filter
		ldap_filter = "" if not ldap_filter else ldap_filter
		identity = None if not identity else identity
		if identity and not identity_filter:
			identity_filter = f"(|(samAccountName={identity})(name={identity})(displayname={identity})(objectSid={identity})(distinguishedName={identity})(dnshostname={identity}))"
		
		if not searchbase:
			searchbase = args.searchbase if hasattr(args, 'searchbase') and args.searchbase else self.root_dn

		logging.debug(f"[Get-DomainObject] Using search base: {searchbase}")
		if args and args.ldapfilter:
			logging.debug(f'[Get-DomainObject] Using additional LDAP filter from args: {args.ldapfilter}')
			ldap_filter = f"{args.ldapfilter}"

		ldap_filter = f'(&(objectClass=*){identity_filter}{ldap_filter})'
		logging.debug(f'[Get-DomainObject] LDAP search filter: {ldap_filter}')

		entries = []
		entry_generator = self.ldap_session.extend.standard.paged_search(searchbase,ldap_filter,attributes=list(properties), paged_size = 1000, generator=True, controls=controls, search_scope=search_scope, no_cache=no_cache)
		for _entries in entry_generator:
			if _entries['type'] != 'searchResEntry':
				continue
			strip_entry(_entries)
			entries.append(_entries)
		return entries

	def remove_domainobject(self, identity, searchbase=None, args=None, search_scope=ldap3.SUBTREE):
		if not searchbase:
			searchbase = args.searchbase if hasattr(args, 'searchbase') and args.searchbase else self.root_dn

		targetobject = self.get_domainobject(identity=identity, properties=[
			'sAMAccountname',
			'ObjectSID',
			'distinguishedName',
		], searchbase=searchbase, search_scope=search_scope)
		
		# verify if the identity exists
		if len(targetobject) > 1:
			logging.error(f"[Remove-DomainObject] More than one object found")
			return False
		elif len(targetobject) == 0:
			logging.error(f"[Remove-DomainObject] {identity} not found in domain")
			return False

		if isinstance(targetobject, list):
			targetobject_dn = targetobject[0]["attributes"]["distinguishedName"]
		else:
			targetobject_dn = targetobject["attributes"]["distinguishedName"]

		logging.info(f"[Remove-DomainObject] Found {targetobject_dn} in domain")
		
		logging.warning(f"[Remove-DomainObject] Removing object from domain")
		
		succeeded = self.ldap_session.delete(targetobject_dn)

		if not succeeded:
			logging.error(self.ldap_session.result['message'] if self.args.debug else f"[Remove-DomainObject] Failed to modify, view debug message with --debug")
		else:
			logging.info(f'[Remove-DomainObject] Success! {targetobject_dn} removed')
		
		return succeeded

	def get_domainobjectowner(self, identity=None, searchbase=None, args=None, search_scope=ldap3.SUBTREE, no_cache=False):
		if not searchbase:
			searchbase = args.searchbase if hasattr(args, 'searchbase') and args.searchbase else self.root_dn
		
		if not identity:
			identity = '*'
			logging.info("[Get-DomainObjectOwner] Recursing all domain objects. This might take a while")

		no_cache = args.no_cache if hasattr(args, 'no_cache') and args.no_cache else no_cache

		objects = self.get_domainobject(identity=identity, properties=[
			'cn',
			'nTSecurityDescriptor',
			'sAMAccountname',
			'objectSid',
			'distinguishedName',
		], searchbase=searchbase, sd_flag=0x01, search_scope=search_scope, no_cache=no_cache)

		if len(objects) == 0:
			logging.error("[Get-DomainObjectOwner] Identity not found in domain")
			return

		for i in range(len(objects)):
			ownersid = None
			parser = ObjectOwner(objects[i])
			ownersid = parser.read()
			ownersid = "%s (%s)" % (self.convertfrom_sid(ownersid), ownersid)
			objects[i] = modify_entry(
				objects[i],
				new_attributes = {
					"Owner": ownersid
				},
				remove = [
					'nTSecurityDescriptor'
				]
			)

		return objects

	def get_domainou(self, args=None, properties=[], identity=None, searchbase=None, resolve_gplink=False, search_scope=ldap3.SUBTREE):
		def_prop = [
			'objectClass',
			'ou',
			'distinguishedName',
			'instanceType',
			'whenCreated',
			'whenChanged',
			'uSNCreated',
			'uSNChanged',
			'name',
			'objectGUID',
			'objectCategory',
			'gPLink',
			'dSCorePropagationData'
		]

		properties = set(properties or def_prop)
		ldap_filter = ""
		identity_filter = "" 

		if identity:
			identity_filter += f"(|(name={identity})(distinguishedName={identity}))"

		if not searchbase:
			searchbase = args.searchbase if hasattr(args, 'searchbase') and args.searchbase else self.root_dn
		
		if args:
			if args.gplink:
				ldap_filter += f"(gplink=*{args.gplink}*)"
			if args.ldapfilter:
				logging.debug(f'[Get-DomainOU] Using additional LDAP filter: {args.ldapfilter}')
				ldap_filter += f"{args.ldapfilter}"

		ldap_filter = f'(&(objectCategory=organizationalUnit){identity_filter}{ldap_filter})'
		logging.debug(f'[Get-DomainOU] LDAP search filter: {ldap_filter}')
		entries = []
		entry_generator = self.ldap_session.extend.standard.paged_search(searchbase,ldap_filter,attributes=list(properties), paged_size = 1000, generator=True, search_scope=search_scope)
		for _entries in entry_generator:
			if _entries['type'] != 'searchResEntry':
				continue
			strip_entry(_entries)

			if resolve_gplink:
				gplinks = re.findall(r"(\{{0,1}([0-9a-fA-F]){8}-([0-9a-fA-F]){4}-([0-9a-fA-F]){4}-([0-9a-fA-F]){4}-([0-9a-fA-F]){12}\}{0,1})",_entries["attributes"]["gPLink"],re.M)
				if gplinks:
					gplink_list = []
					for guid in [guids[0] for guids in gplinks]:
						gpo = self.get_domaingpo(identity=guid, properties=["displayName"])
						if len(gpo) == 0:
							logging.debug("[Get-DomainOU] gPLink not found. Cant resolve %s" % (guid))
						elif len(gpo) > 1:
							logging.debug("[Get-DomainOU] More than one gPLink found for %s. Ignoring..." % (guid))
						else:
							gplink_list.append("{} ({})".format(guid, gpo[0].get("attributes").get("displayName")))
					
					if len(gplink_list) != 0:
						_entries["attributes"]["gPLink"] = gplink_list

			entries.append(_entries)
		return entries
		#self.ldap_session.search(self.root_dn,ldap_filter,attributes=properties)
		#return self.ldap_session.entries

	def get_domainobjectacl(self, identity=None, security_identifier=None, resolveguids=False, targetidentity=None, principalidentity=None, guids_map_dict=None, searchbase=None, args=None, search_scope=ldap3.SUBTREE, no_cache=False):
		# Use args to set defaults if not provided directly
		if args:
			identity = identity or getattr(args, 'identity', None)
			security_identifier = security_identifier or getattr(args, 'security_identifier', None)
			searchbase = searchbase or getattr(args, 'searchbase', self.root_dn)

		# Use the provided searchbase or default to the root DN
		if not searchbase:
			searchbase = self.root_dn

		no_cache = args.no_cache if hasattr(args, 'no_cache') and args.no_cache else no_cache

		# Enumerate available GUIDs
		guids_dict = {}
		try:
			logging.debug(f"[Get-DomainObjectAcl] Searching for GUIDs in {self.root_dn}")
			guid_generator = self.ldap_session.extend.standard.paged_search(f"CN=Extended-Rights,CN=Configuration,{self.root_dn}", "(rightsGuid=*)", attributes=['displayName', 'rightsGuid'], paged_size=1000, generator=True, search_scope=search_scope, no_cache=no_cache)
			for entry in guid_generator:
				if entry['type'] != 'searchResEntry':
					continue
				rights_guid = entry['attributes'].get('rightsGuid')
				display_name = entry['attributes'].get('displayName')

				if isinstance(rights_guid, list):
					rights_guid = rights_guid[0]
				if isinstance(display_name, list):
					display_name = display_name[0]

				if rights_guid and display_name:
					guids_dict[rights_guid] = display_name
		except ldap3.core.exceptions.LDAPOperationResult as e:
			logging.error(f"[Get-DomainObjectAcl] Error searching for GUIDs in {self.root_dn}: {e}. Continuing...")

		principal_SID = None
		if security_identifier:
			principalsid_entry = self.get_domainobject(identity=security_identifier, properties=['objectSid'], no_cache=no_cache, searchbase=searchbase)
			if not principalsid_entry:
				logging.debug('[Get-DomainObjectAcl] Principal not found. Searching in Well Known SIDs...')
				principal_SID = resolve_WellKnownSID(security_identifier)

				if principal_SID:
					principal_SID = principal_SID.get("objectSid")
					logging.debug("[Get-DomainObjectAcl] Found in well known SID: %s" % principal_SID)
				else:
					logging.error(f'[Get-DomainObjectAcl] Principal {security_identifier} not found. Try to use DN')
					return

			elif len(principalsid_entry) > 1:
				logging.error(f'[Get-DomainObjectAcl] Multiple identities found. Use exact match')
				return

			security_identifier = principalsid_entry[0]['attributes']['objectSid'] if not principal_SID else principal_SID

		if identity != "*":
			identity_entries = self.get_domainobject(identity=identity, properties=['objectSid', 'distinguishedName'], searchbase=searchbase, no_cache=no_cache)
			if len(identity_entries) == 0:
				logging.error(f'[Get-DomainObjectAcl] Identity {identity} not found. Try to use DN')
				return
			elif len(identity_entries) > 1:
				logging.error(f'[Get-DomainObjectAcl] Multiple identities found. Use exact match')
				return
			logging.debug(f'[Get-DomainObjectAcl] Target identity found in domain {"".join(identity_entries[0]["attributes"]["distinguishedName"])}')
			identity = "".join(identity_entries[0]['attributes']['distinguishedName'])
		else:
			logging.info('[Get-DomainObjectAcl] Recursing all domain objects. This might take a while')

		logging.debug(f"[Get-DomainObjectAcl] Searching for identity %s" % (identity))
		
		entries = []
		entry_generator = self.ldap_session.extend.standard.paged_search(searchbase, f'(distinguishedName={identity})', attributes=['nTSecurityDescriptor', 'sAMAccountName', 'distinguishedName', 'objectSid'], controls=security_descriptor_control(sdflags=0x04), paged_size=1000, generator=True, search_scope=search_scope, no_cache=no_cache)
		for _entries in entry_generator:
			if _entries['type'] != 'searchResEntry':
				continue
			entries.append(_entries)

		if not entries:
			logging.error(f'[Get-DomainObjectAcl] Identity not found in domain')
			return

		enum = ACLEnum(self, entries, searchbase, resolveguids=resolveguids, targetidentity=identity, principalidentity=security_identifier, guids_map_dict=guids_dict)
		entries_dacl = enum.read_dacl()
		return entries_dacl

	def get_domaincomputer(self, args=None, properties=[], identity=None, searchbase=None, resolveip=False, resolvesids=False, ldapfilter=None, search_scope=ldap3.SUBTREE, no_cache=False):
		def_prop = [
			'lastLogonTimestamp',
			'objectCategory',
			'servicePrincipalName',
			'dNSHostName',
			'sAMAccountType',
			'sAMAccountName',
			'logonCount',
			'objectSid',
			'primaryGroupID',
			'pwdLastSet',
			'lastLogon',
			'lastLogoff',
			'badPasswordTime',
			'badPwdCount',
			'userAccountControl',
			'objectGUID',
			'name',
			'instanceType',
			'distinguishedName',
			'cn',
			'operatingSystem',
			'msDS-SupportedEncryptionTypes',
			'description'
		]

		if args and hasattr(args, 'properties') and args.properties:
			properties = set(args.properties)
		else:
			properties = set(properties or def_prop)

		no_cache = args.no_cache if hasattr(args, 'no_cache') and args.no_cache else no_cache
		
		if not searchbase:
			searchbase = args.searchbase if hasattr(args, 'searchbase') and args.searchbase else self.root_dn

		logging.debug(f"[Get-DomainComputer] Using search base: {searchbase}")
		
		ldap_filter = ""
		identity_filter = ""

		if identity:
			identity_filter += f"(|(name={identity})(sAMAccountName={identity})(dnsHostName={identity}))"
		elif args and hasattr(args, 'identity') and args.identity:
			identity_filter += f"(|(name={args.identity})(sAMAccountName={args.identity})(dnsHostName={args.identity}))"

		if ldapfilter:
			ldap_filter += ldapfilter

		if args:
			if hasattr(args, 'unconstrained') and args.unconstrained:
				logging.debug("[Get-DomainComputer] Searching for computers with unconstrained delegation")
				ldap_filter += f'(userAccountControl:1.2.840.113556.1.4.803:=524288)'
			if hasattr(args, 'enabled') and args.enabled:
				logging.debug("[Get-DomainComputer] Searching for enabled computer")
				ldap_filter += f'(!(userAccountControl:1.2.840.113556.1.4.803:=2))'
			if hasattr(args, 'disabled') and args.disabled:
				logging.debug("[Get-DomainComputer] Searching for disabled computer")
				ldap_filter += f'(userAccountControl:1.2.840.113556.1.4.803:=2)'
			if hasattr(args, 'trustedtoauth') and args.trustedtoauth:
				logging.debug("[Get-DomainComputer] Searching for computers that are trusted to authenticate for other principals")
				ldap_filter += f'(msds-allowedtodelegateto=*)'
				properties.add('msds-AllowedToDelegateTo')
			if hasattr(args, 'laps') and args.laps:
				logging.debug("[Get-DomainComputer] Searching for computers with LAPS enabled")
				ldap_filter += f'(ms-Mcs-AdmPwd=*)'
				properties += ['ms-MCS-AdmPwd','ms-Mcs-AdmPwdExpirationTime']
			if hasattr(args, 'rbcd') and args.rbcd:
				logging.debug("[Get-DomainComputer] Searching for computers that are configured to allow resource-based constrained delegation")
				ldap_filter += f'(msds-allowedtoactonbehalfofotheridentity=*)'
				properties.add('msDS-AllowedToActOnBehalfOfOtherIdentity')
			if hasattr(args, 'shadowcred') and args.shadowcred:
				logging.debug("[Get-DomainComputer] Searching for computers that are configured to have msDS-KeyCredentialLink attribute set")
				ldap_filter += f'(msDS-KeyCredentialLink=*)'
				properties.add('msDS-KeyCredentialLink')
			if hasattr(args, 'printers') and args.printers:
				logging.debug("[Get-DomainComputer] Searching for printers")
				ldap_filter += f'(objectCategory=printQueue)'
			if hasattr(args, 'spn') and args.spn:
				logging.debug(f"[Get-DomainComputer] Searching for computers with SPN attribute: {args.spn}")
				ldap_filter += f'(servicePrincipalName=*)'
			if hasattr(args, 'excludedcs') and args.excludedcs:
				logging.debug("[Get-DomainComputer] Excluding domain controllers")
				ldap_filter += f'(!(userAccountControl:1.2.840.113556.1.4.803:=8192))'
			if hasattr(args, 'bitlocker') and args.bitlocker:
				logging.debug("[Get-DomainComputer] Searching for computers with BitLocker keys")
				ldap_filter += f'(objectClass=msFVE-RecoveryInformation)'
				properties.add('msFVE-KeyPackage')
				properties.add('msFVE-RecoveryGuid')
				properties.add('msFVE-RecoveryPassword')
				properties.add('msFVE-VolumeGuid')
			if hasattr(args, 'gmsapassword') and args.gmsapassword:
				logging.debug("[Get-DomainComputer] Searching for computers with GSMA password stored")
				ldap_filter += f'(objectClass=msDS-GroupManagedServiceAccount)'
				properties.add('msDS-ManagedPassword')
				properties.add('msDS-GroupMSAMembership')
				properties.add('msDS-ManagedPasswordInterval')
				properties.add('msDS-ManagedPasswordId')
			if hasattr(args, 'pre2k') and args.pre2k:
				logging.debug("[Get-DomainComputer] Search for Pre-Created Windows 2000 computer")
				ldap_filter += f'(userAccountControl=4128)(logonCount=0)'
			if hasattr(args, 'ldapfilter') and args.ldapfilter:
				logging.debug(f'[Get-DomainComputer] Using additional LDAP filter: {args.ldapfilter}')
				ldap_filter += f"{args.ldapfilter}"

		ldap_filter = f'(&(objectClass=computer){identity_filter}{ldap_filter})'
		logging.debug(f'[Get-DomainComputer] LDAP search filter: {ldap_filter}')
		entries = []
		entry_generator = self.ldap_session.extend.standard.paged_search(searchbase,ldap_filter,attributes=list(properties), paged_size = 1000, generator=True, search_scope=search_scope, no_cache=no_cache)
		for _entries in entry_generator:
			if _entries['type'] != 'searchResEntry':
				continue
			strip_entry(_entries)
			#if (_entries['attributes']['dnsHostName'], list):
			#    dnshostname = _entries['attributes']['dnsHostName'][0]
			#else:
			#    dnshostname = _entries['attributes']['dnsHostName']
			#if not dnshostname:
			#    continue
			if resolveip and _entries.get('attributes').get('dnsHostName'):
				ip = host2ip(_entries['attributes']['dnsHostName'], self.nameserver, 3, True, use_system_ns=self.use_system_nameserver, type=list)
				_entries = modify_entry(
					_entries,
					new_attributes = {
						'IPAddress':ip
					}
				)
			# resolve msDS-AllowedToActOnBehalfOfOtherIdentity
			try:
				if "msDS-AllowedToActOnBehalfOfOtherIdentity" in list(_entries["attributes"].keys()):
					parser = RBCD(_entries)
					sids = parser.read()
					if args.resolvesids:
						for i in range(len(sids)):
							sids[i] = self.convertfrom_sid(sids[i])
					_entries["attributes"]["msDS-AllowedToActOnBehalfOfOtherIdentity"] = sids
			except:
				pass

			# resolve msDS-GroupMSAMembership
			try:
				if "msDS-GroupMSAMembership" in list(_entries["attributes"].keys()):
					_entries["attributes"]["msDS-GroupMSAMembership"] = self.convertfrom_sid(_entries["attributes"]["msDS-GroupMSAMembership"])
			except:
				pass

			entries.append(_entries)
		return entries

	def get_domaingmsa(self, identity=None, args=None):
		properties = [
			"sAMAccountName",
			"objectSid",
			"dnsHostName",
			"msDS-GroupMSAMembership",
			"msDS-ManagedPassword"
		]

		entries = []
		searchbase = args.searchbase if hasattr(args, 'searchbase') and args.searchbase else self.root_dn

		setattr(args, "ldapfilter", "(&(objectClass=msDS-GroupManagedServiceAccount))")

		# get source identity
		sourceObj = self.get_domainobject(identity=identity, properties=properties, searchbase=searchbase, args=args, sd_flag=0x04)

		logging.debug("[Get-DomainGMSA] Found %d object(s) with gmsa attribute" % (len(sourceObj)))

		if not sourceObj:
			return

		for source in sourceObj:
			source = source.get("attributes")

			# resolve sid
			if isinstance(source.get("msDS-GroupMSAMembership"), list):
				for i in range(len(source.get("msDS-GroupMSAMembership"))):
					source["msDS-GroupMSAMembership"][i] = self.convertfrom_sid(source["msDS-GroupMSAMembership"][i])
			else:
				source["msDS-GroupMSAMembership"] = self.convertfrom_sid(source["msDS-GroupMSAMembership"])

			entry = {
				"ObjectDnsHostname": source.get("dnsHostname"),
				"ObjectSAN": source.get("sAMAccountName"),
				"ObjectSID": source.get("objectSid"),
				"PrincipallAllowedToRead": source.get("msDS-GroupMSAMembership"),
				"GMSAPassword": source.get("msDS-ManagedPassword")
			}

			entries.append(
				{
					"attributes": dict(entry)
				}
			)

		return entries

	def get_domainrbcd(self, identity=None, args=None):
		properties = [
					"sAMAccountName",
					"sAMAccountType",
					"objectSID",
					"userAccountControl",
					"distinguishedName",
					"servicePrincipalName",
					"msDS-AllowedToActOnBehalfOfOtherIdentity"
				] 

		entries = []
		searchbase = args.searchbase if hasattr(args, 'searchbase') and args.searchbase else self.root_dn

		# set args to have rbcd attribute
		setattr(args, "ldapfilter", "(msDS-AllowedToActOnBehalfOfOtherIdentity=*)")

		# get source identity
		sourceObj = self.get_domainobject(identity=identity, properties=properties, searchbase=searchbase, args=args)

		logging.debug("[Get-DomainRBCD] Found %d object(s) with msDS-AllowedToActOnBehalfOfOtherIdentity attribute" % (len(sourceObj)))

		if not sourceObj:
			return

		for source in sourceObj:
			entry = {
				"SourceName": None,
				"SourceType": None,
				"SourceSID": None,
				"SourceAccountControl": None,
				"SourceDistinguishedName": None,
				"ServicePrincipalName": None,
				"DelegatedName": None,
				"DelegatedType": None,
				"DelegatedSID": None,
				"DelegatedAccountControl": None,
				"DelegatedDistinguishedName": None,
			}

			# resolve msDS-AllowedToActOnBehalfOfOtherIdentity
			parser = RBCD(source)
			sids = parser.read()

			source = source.get("attributes")
			entry["SourceName"] = source.get("sAMAccountName")
			entry["SourceType"] = source.get("sAMAccountType")
			entry["SourceSID"] = source.get("objectSid")
			entry["SourceAccountControl"] = source.get("userAccountControl")
			entry["SourceDistinguishedName"] = source.get("distinguishedName")
			entry["ServicePrincipalName"] = source.get("servicePrincipalName")

			for sid in sids:
				# resolve sid from delegateObj
				delegateObj = self.get_domainobject(identity=sid, properties=properties, searchbase=searchbase)
				if len(delegateObj) == 0:
					logging.warning("Delegated object not found. Ignoring...")
				elif len(delegateObj) > 1:
					logging.warning("More than one delegated object found. Ignoring...")

				for delegate in delegateObj:
					try:
						delegate = delegate.get("attributes")
						entry["DelegatedName"] = delegate.get("sAMAccountName")
						entry["DelegatedType"] = delegate.get("sAMAccountType")
						entry["DelegatedSID"] = delegate.get("objectSid")
						entry["DelegatedAccountControl"] = delegate.get("userAccountControl")
						entry["DelegatedDistinguishedName"] = delegate.get("distinguishedName")
					except IndexError:
						logging.error(f"[IndexError] No object found for {sid}")
						pass
				
				entries.append(
							{
								"attributes": dict(entry)
							}
						)
		return entries

	def get_domaingroup(self, args=None, properties=[], identity=None, searchbase=None, search_scope=ldap3.SUBTREE, no_cache=False):
		def_prop = [
			'adminCount',
			'cn',
			'description',
			'distinguishedName',
			'groupType',
			'instanceType',
			'member',
			'objectCategory',
			'objectGUID',
			'objectSid',
			'sAMAccountName',
			'sAMAccountType',
			'name'
		]

		properties = set(properties or def_prop)
		if not searchbase:
			searchbase = args.searchbase if hasattr(args, 'searchbase') and args.searchbase else self.root_dn

		no_cache = args.no_cache if hasattr(args, 'no_cache') and args.no_cache else no_cache

		logging.debug(f"[Get-DomainGroup] Using search base: {searchbase}")
		
		ldap_filter = ""
		identity_filter = ""

		if identity:
			identity_filter += f"(|(|(samAccountName={identity})(name={identity})(distinguishedName={identity})))"

		if args:
			if args.admincount:
				ldap_filter += f"(admincount=1)"
			if args.ldapfilter:
				ldap_filter += f"{args.ldapfilter}"
				logging.debug(f'[Get-DomainGroup] Using additional LDAP filter: {args.ldapfilter}')
			if args.memberidentity:
				entries = self.get_domainobject(identity=args.memberidentity)
				if len(entries) == 0:
					logging.info("Member identity not found. Try to use DN")
					return
				memberidentity_dn = entries[0]['attributes']['distinguishedName']
				ldap_filter += f"(member={memberidentity_dn})"
				logging.debug(f'[Get-DomainGroup] Filter is based on member property {ldap_filter}')

		ldap_filter = f'(&(objectCategory=group){identity_filter}{ldap_filter})'
		logging.debug(f'[Get-DomainGroup] LDAP search filter: {ldap_filter}')
		entries = []
		entry_generator = self.ldap_session.extend.standard.paged_search(searchbase,ldap_filter,attributes=list(properties), paged_size = 1000, generator=True, search_scope=search_scope, no_cache=no_cache)
		for _entries in entry_generator:
			if _entries['type'] != 'searchResEntry':
				continue
			strip_entry(_entries)
			entries.append(_entries)
		return entries

	def get_domainforeigngroupmember(self, args=None):
		group_members = self.get_domaingroupmember(identity='*', multiple=True)
		cur_domain_sid = self.get_domain()[0]['attributes']['objectSid']

		if not group_members:
			logging.info("[Get-DomainForeignGroupMember] No group members found")
			return
		
		new_entries = []
		for member in group_members:
			member_sid = member['attributes']['MemberSID']
			if cur_domain_sid not in member_sid:
				new_entries.append(member)

		return new_entries

	def get_domainforeignuser(self, args=None):
		domain_users = self.get_domainuser()

		entries = []
		for user in domain_users:
			user_san = user['attributes']['sAMAccountName']
			user_memberof = user['attributes']['memberOf']
			if isinstance(user_memberof, str):
				user_memberof = [user_memberof]

			for group in user_memberof:
				group_domain = dn2domain(group)
				group_root_dn = dn2rootdn(group)
				if group_domain.casefold() != self.domain.casefold():
					_, ldap_session = self.conn.init_ldap_session(ldap_address=group_domain)
					ldap_filter = f"(&(objectCategory=group)(distinguishedName={group}))"
					succeed = ldap_session.search(group_root_dn, ldap_filter, attributes='*')
					if not succeed:
						logging.error("[Get-DomainForeignUser] Failed ldap query")
					if ldap_session.entries:
						ent = ldap_session.entries[0]
					entries.append(
							{'attributes':{
									'UserDomain': dn2domain(user['attributes']['distinguishedName']),
									'UserName': user_san,
									'UserDistinguishedName': user['attributes']['distinguishedName'],
									'GroupDomain': group_domain,
									'GroupName': ent['name'].value,
									'GroupDistinguishedName': group
								}
							 }
							)

		return entries


	def get_domaingroupmember(self, identity, args=None, multiple=False):
		# get the identity group information
		entries = self.get_domaingroup(identity=identity)

		if len(entries) == 0:
			logging.warning("[Get-DomainGroupMember] No group found")
			return

		if len(entries) > 1 and not multiple:
			logging.warning("[Get-DomainGroupMember] Multiple group found. Probably try searching with distinguishedName")
			return

		# create a new entry structure
		new_entries = []
		for ent in entries:
			haveForeign = False
			group_identity_sam = ent['attributes']['sAMAccountName']
			group_identity_dn = ent['attributes']['distinguishedName']
			group_members = ent['attributes']['member']
			if isinstance(group_members, str):
				group_members = [group_members]
			
			for dn in group_members:
				if len(dn) != 0 and dn2domain(dn).casefold() != self.domain.casefold():
					haveForeign = True
					break

			if haveForeign:
				for member_dn in group_members:
					member_root_dn = dn2rootdn(member_dn)
					member_domain = dn2domain(member_dn)
					ldap_filter = f"(&(objectCategory=*)(|(distinguishedName={member_dn})))"

					if len(member_domain) != 0 and member_domain.casefold() != self.domain.casefold():
						_, ldap_session = self.conn.init_ldap_session(ldap_address=member_domain)
						succeed = ldap_session.search(member_root_dn, ldap_filter, attributes='*')
						if not succeed:
							logging.error(f"[Get-DomainGroupMember] Failed to query for {member_dn}")
							return
						entries = ldap_session.entries
					else:
						self.ldap_session.search(self.root_dn, ldap_filter, attributes='*')
						entries = self.ldap_session.entries

					for ent in entries:
						attr = {}
						member_infos = {}
						try:
							member_infos['GroupDomainName'] = group_identity_sam
						except:
							pass
						try:
							member_infos['GroupDistinguishedName'] = group_identity_dn
						except:
							pass
						try:
							member_infos['MemberDomain'] = ent['userPrincipalName'].value.split("@")[-1]
						except:
							member_infos['MemberDomain'] = self.domain
						try:
							member_infos['MemberName'] = ent['sAMAccountName'].value
						except:
							pass
						try:
							member_infos['MemberDistinguishedName'] = ent['distinguishedName'].value
						except:
							pass
						try:
							member_infos['MemberSID'] = ent['objectSid'].value
						except:
							pass

						attr['attributes'] = member_infos
						new_entries.append(attr.copy())
			else:
				ldap_filter = f"(&(objectCategory=*)(memberof:1.2.840.113556.1.4.1941:={group_identity_dn}))"
				self.ldap_session.search(self.root_dn, ldap_filter, attributes='*')

				for entry in self.ldap_session.entries:
					attr = {}
					member_infos = {}
					try:
						member_infos['GroupDomainName'] = group_identity_sam
					except:
						pass
					try:
						member_infos['GroupDistinguishedName'] = group_identity_dn
					except:
						pass
					try:
						member_infos['MemberDomain'] = entry['userPrincipalName'].value.split("@")[-1]
					except:
						member_infos['MemberDomain'] = self.domain
					try:
						member_infos['MemberName'] = entry['sAMAccountName'].value
					except:
						pass
					try:
						member_infos['MemberDistinguishedName'] = entry['distinguishedName'].value
					except:
						pass
					try:
						member_infos['MemberSID'] = entry['objectSid'].value
					except:
						pass

					attr['attributes'] = member_infos
					new_entries.append(attr.copy())

		return new_entries

	def get_domaingpo(self, args=None, properties=[], identity=None, searchbase=None, search_scope=ldap3.SUBTREE):
		def_prop = [
			'objectClass',
			'cn',
			'distinguishedName',
			'instanceType',
			'whenCreated',
			'whenChanged',
			'displayName',
			'uSNCreated',
			'uSNChanged',
			'showInAdvancedViewOnly',
			'name',
			'objectGUID',
			'flags',
			'versionNumber',
			'systemFlags',
			'objectCategory',
			'isCriticalSystemObject',
			'gPCFunctionalityVersion',
			'gPCFileSysPath',
			'gPCMachineExtensionNames',
			'dSCorePropagationData'
		]

		properties = set(properties or def_prop)
		ldap_filter = ""
		identity_filter = ""
		if identity:
			identity_filter = f"(|(cn=*{identity}*)(displayName={identity}))"
		
		if not searchbase:
			searchbase = args.searchbase if hasattr(args, 'searchbase') and args.searchbase else self.root_dn

		if args:
			if args.ldapfilter:
				logging.debug(f'[Get-DomainGPO] Using additional LDAP filter: {args.ldapfilter}')
				ldap_filter += f"{args.ldapfilter}"

		ldap_filter = f'(&(objectCategory=groupPolicyContainer){identity_filter}{ldap_filter})'
		logging.debug(f'[Get-DomainGPO] LDAP search filter: {ldap_filter}')
		entries = []
		entry_generator = self.ldap_session.extend.standard.paged_search(searchbase,ldap_filter,attributes=list(properties), paged_size = 1000, generator=True, search_scope=search_scope)
		for _entries in entry_generator:
			if _entries['type'] != 'searchResEntry':
				continue
			strip_entry(_entries)
			entries.append(_entries)
		return entries

	def get_domaingpolocalgroup(self, args=None, identity=None):
		new_entries = []
		entries = self.get_domaingpo(identity=identity)
		if len(entries) == 0:
			logging.error("[Get-DomainGPOLocalGroup] No GPO object found")
			return
		for entry in entries:
			new_dict = {}
			try:
				gpcfilesyspath = f"{entry['attributes']['gPCFileSysPath']}\\MACHINE\\Microsoft\\Windows NT\\SecEdit\\GptTmpl.inf"

				conn = self.conn.init_smb_session(host2ip(self.dc_ip, self.nameserver, 3, True, use_system_ns=self.use_system_nameserver))

				share = 'sysvol'
				filepath = ''.join(gpcfilesyspath.lower().split(share)[1:])

				fh = BytesIO()
				try:
					conn.getFile(share, filepath, fh.write)
				except:
					pass
				output = fh.getvalue()
				encoding = chardet.detect(output)["encoding"]
				error_msg = "[-] Output cannot be correctly decoded, are you sure the text is readable ?"
				if encoding:
					data_content = output.decode(encoding)
					found, infobject = parse_inicontent(filecontent=data_content)
					if found:
						if len(infobject) == 2:
							new_dict['attributes'] = {'GPODisplayName': entry['attributes']['displayName'], 'GPOName': entry['attributes']['name'], 'GPOPath': entry['attributes']['gPCFileSysPath'], 'GroupName': self.convertfrom_sid(infobject[0]['sids']),'GroupSID':infobject[0]['sids'],'GroupMemberOf': f"{infobject[0]['memberof']}" if infobject[0]['memberof'] else "{}", 'GroupMembers': f"{infobject[1]['members']}" if infobject[1]['members'] else "{}"}
							new_entries.append(new_dict.copy())
						else:
							for i in range(0,len(infobject),2):
								new_dict['attributes'] = {'GPODisplayName': entry['attributes']['displayName'], 'GPOName': entry['attributes']['name'], 'GPOPath': entry['attributes']['gPCFileSysPath'], 'GroupName':self.convertfrom_sid(infobject[0]['sids']) ,'GroupSID':infobject[i]['sids'],'GroupMemberOf': f"{infobject[i]['memberof']}" if infobject[i]['memberof'] else "{}", 'GroupMembers': f"{infobject[i+1]['members']}" if infobject[i+1]['members'] else "{}"}
								new_entries.append(new_dict.copy())
					fh.close()
				else:
					fh.close()
					continue

			except ldap3.core.exceptions.LDAPKeyError as e:
				pass
		return new_entries

	def get_domaingposettings(self, args=None, identity=None):
		"""
		Parse GPO settings from SYSVOL share
		Returns dictionary containing Machine and User configurations
		"""
		if args and hasattr(args, 'identity'):
			identity = args.identity

		entries = self.get_domaingpo(identity=identity)
		if len(entries) == 0:
			logging.error("[Get-GPOSettings] No GPO object found")
			return

		policy_settings = []
		for entry in entries:
			try:
				gpcfilesyspath = entry['attributes']['gPCFileSysPath']
				
				# Connect to SYSVOL share
				conn = self.conn.init_smb_session(host2ip(self.dc_ip, self.nameserver, 3, True, use_system_ns=self.use_system_nameserver))
				share = 'sysvol'
				base_path = ''.join(gpcfilesyspath.lower().split(share)[1:])
				
				policy_data = {
					'attributes': {
						'displayName': entry['attributes']['displayName'],
						'name': entry['attributes']['name'],
						'gPCFileSysPath': gpcfilesyspath,
						'machineConfig': {},
						'userConfig': {}
					}
				}

				# Parse Machine Configuration
				machine_paths = {
					'Security': '\\MACHINE\\Microsoft\\Windows NT\\SecEdit\\GptTmpl.inf',
					'Registry': '\\MACHINE\\Registry.pol',
					'Scripts': '\\MACHINE\\Scripts\\scripts.ini',
					'Preferences': '\\MACHINE\\Preferences'
				}

				# Parse User Configuration
				user_paths = {
					'Registry': '\\USER\\Registry.pol',
					'Scripts': '\\USER\\Scripts\\scripts.ini',
					'Preferences': '\\USER\\Preferences'
				}

				# Process Machine Configuration
				for section, path in machine_paths.items():
					try:
						fh = BytesIO()
						file_path = base_path + path
						try:
							conn.getFile(share, file_path, fh.write)
							content = fh.getvalue()
							encoding = chardet.detect(content)["encoding"]
							if encoding:
								data = content.decode(encoding)
								if section == 'Security':
									# Parse Security Settings (GptTmpl.inf)
									policy_data['attributes']['machineConfig']['Security'] = GPO.Helper._parse_inf_file(data)
								elif section == 'Registry':
									# Parse Registry Settings
									policy_data['attributes']['machineConfig']['Registry'] = GPO.Helper._parse_registry_pol(content)
								elif section == 'Scripts':
									# Parse Startup/Shutdown Scripts
									policy_data['attributes']['machineConfig']['Scripts'] = GPO.Helper._parse_scripts_ini(data)
								elif section == 'Preferences':
									# Parse Group Policy Preferences
									policy_data['attributes']['machineConfig']['Preferences'] = GPO.Helper._parse_preferences(file_path, conn, share)
						except Exception as e:
							logging.debug(f"[Get-GPOSettings] File not found or access denied: {file_path}")
						finally:
							fh.close()
					except Exception as e:
						logging.debug(f"[Get-GPOSettings] Error processing {section}: {str(e)}")

				# Process User Configuration (similar structure to Machine Configuration)
				for section, path in user_paths.items():
					try:
						fh = BytesIO()
						file_path = base_path + path
						try:
							conn.getFile(share, file_path, fh.write)
							content = fh.getvalue()
							encoding = chardet.detect(content)["encoding"]
							if encoding:
								data = content.decode(encoding)
								if section == 'Registry':
									policy_data['attributes']['userConfig']['Registry'] = GPO.Helper._parse_registry_pol(content)
								elif section == 'Scripts':
									policy_data['attributes']['userConfig']['Scripts'] = GPO.Helper._parse_scripts_ini(data)
								elif section == 'Preferences':
									policy_data['attributes']['userConfig']['Preferences'] = GPO.Helper._parse_preferences(file_path, conn, share)
						except Exception as e:
							logging.debug(f"[Get-GPOSettings] File not found or access denied: {file_path}")
						finally:
							fh.close()
					except Exception as e:
						logging.debug(f"[Get-GPOSettings] Error processing {section}: {str(e)}")

				policy_settings.append(policy_data)

			except Exception as e:
				logging.error(f"[Get-GPOSettings] Error processing GPO: {str(e)}")
				continue
		return policy_settings

	def get_domaintrust(self, args=None, properties=[], identity=None, searchbase=None, search_scope=ldap3.SUBTREE, no_cache=False):
		def_prop = [
			'name',
			'objectGUID',
			'securityIdentifier',
			'trustDirection',
			'trustPartner',
			'trustType',
			'trustAttributes',
			'flatName'
		]

		properties = set(properties or def_prop)
		identity = '*' if not identity else identity

		if not searchbase:
			searchbase = args.searchbase if hasattr(args, 'searchbase') and args.searchbase else self.root_dn

		no_cache = args.no_cache if hasattr(args, 'no_cache') and args.no_cache else no_cache

		identity_filter = f"(name={identity})"
		ldap_filter = f'(&(objectClass=trustedDomain){identity_filter})'
		logging.debug(f'[Get-DomainTrust] LDAP search filter: {ldap_filter}')

		entries = []
		entry_generator = self.ldap_session.extend.standard.paged_search(searchbase, ldap_filter,attributes=list(properties), paged_size = 1000, generator=True, search_scope=search_scope, no_cache=no_cache)
		for _entries in entry_generator:
			if _entries['type'] != 'searchResEntry':
				continue
			strip_entry(_entries)
			entries.append(_entries)
		return entries

	def convertto_uacvalue(self, value, args=None, output=False):
		if value.isdigit() or not isinstance(value, str):
			raise ValueError("Value is not a string")

		logging.debug(f"[ConvertTo-UACValue] Converting UAC name to value: {value}")
		value = LDAP.parse_uac_name_to_value(value)
		entries = [
			{
				"attributes": {
					"Name": value.split(','),
					"UACValue": value
				}
			}
		]
		return entries

	def convertfrom_uacvalue(self, value, args=None, output=False):
		values = UAC.parse_value_tolist(value)
		entries = []
		for v in values:
			entry = {
				"Name": v[0],
				"Value": v[1],
			}
			entries.append(
				{
					"attributes": dict(entry)
				}
			)
		return entries

	def convertfrom_sid(self, objectsid, args=None, output=False, no_cache=False):
		no_cache = args.no_cache if hasattr(args, 'no_cache') and args.no_cache else no_cache
		identity = WELL_KNOWN_SIDS.get(objectsid)
		known_sid = KNOWN_SIDS.get(objectsid)
		if identity:
			identity = identity
		elif known_sid:
			logging.debug(f"[ConvertFrom-SID] Using previously stored SID: {known_sid}")
			identity = known_sid
		else:
			ldap_filter = f"(|(|(objectSid={objectsid})))"
			logging.debug(f"[ConvertFrom-SID] LDAP search filter: {ldap_filter}")

			entries = []
			entry_generator = self.ldap_session.extend.standard.paged_search(self.root_dn, ldap_filter, attributes=['sAMAccountName','name'], paged_size=1000, generator=True, no_cache=no_cache)
			for _entries in entry_generator:
				if _entries['type'] != 'searchResEntry':
					continue
				entries.append(_entries)

			if len(entries) == 0:
				logging.debug(f"[ConvertFrom-SID] No objects found for {objectsid}")
				return objectsid
			elif len(entries) > 1:
				logging.warning(f"[ConvertFrom-SID] Multiple objects found for {objectsid}")
				return objectsid

			try:
				sam_account_name = entries[0]['attributes']['sAMAccountName']
				if isinstance(sam_account_name, list):
					sam_account_name = sam_account_name[0]
				identity = f"{self.flatName}\\{sam_account_name}"
			except (IndexError, KeyError):
				try:
					name = entries[0]['attributes']['name']
					if isinstance(name, list):
						name = name[0]
					identity = f"{self.flatName}\\{name}"
				except (IndexError, KeyError):
					return objectsid

			KNOWN_SIDS[objectsid] = identity

		if output:
			print("%s" % identity)
		return identity

	def get_domain(self, args=None, properties=[], identity=None, searchbase=None, search_scope=ldap3.SUBTREE, no_cache=False):
		properties = ['*'] if not properties else properties
		identity = '*' if not identity else identity
		no_cache = args.no_cache if hasattr(args, 'no_cache') and args.no_cache else no_cache

		identity_filter = f"(|(name={identity})(distinguishedName={identity}))"
		if not searchbase:
			searchbase = args.searchbase if hasattr(args, 'searchbase') and args.searchbase else self.root_dn
		ldap_filter = ""

		if args:
			if args.ldapfilter:
				logging.debug(f'[Get-Domain] Using additional LDAP filter: {args.ldapfilter}')
				ldap_filter += f'{args.ldapfilter}'

		ldap_filter = f'(&(objectClass=domain){identity_filter}{ldap_filter})'
		logging.debug(f'[Get-Domain] LDAP search filter: {ldap_filter}')

		entries = []
		entry_generator = self.ldap_session.extend.standard.paged_search(searchbase,ldap_filter,attributes=properties, paged_size = 1000, generator=True, search_scope=search_scope, no_cache=no_cache)
		for _entries in entry_generator:
			if _entries['type'] != 'searchResEntry':
				continue
			strip_entry(_entries)
			entries.append(_entries)
		return entries

	def get_domaindnszone(self, identity=None, properties=[], searchbase=None, args=None, search_scope=ldap3.SUBTREE, no_cache=False):
		def_prop = [
			'objectClass',
			'cn',
			'distinguishedName',
			'instanceType',
			'whenCreated',
			'whenChanged',
			'name',
			'objectGUID',
			'objectCategory',
			'dSCorePropagationData',
			'dc'
		]

		properties = def_prop if not properties else properties
		identity = '*' if not identity else identity
		no_cache = args.no_cache if hasattr(args, 'no_cache') and args.no_cache else no_cache
		
		if not searchbase:
			searchbase = args.searchbase if hasattr(args, 'searchbase') and args.searchbase else f"CN=MicrosoftDNS,DC=DomainDnsZones,{self.root_dn}" 

		identity_filter = f"(name={identity})"
		ldap_filter = f"(&(objectClass=dnsZone){identity_filter})"

		logging.debug(f"[Get-DomainDNSZone] Search base: {searchbase}")
		logging.debug(f"[Get-DomainDNSZone] LDAP Filter string: {ldap_filter}")

		entries = []
		entry_generator = self.ldap_session.extend.standard.paged_search(searchbase, ldap_filter, attributes=properties, paged_size = 1000, generator=True, search_scope=search_scope, no_cache=no_cache)
		for _entries in entry_generator:
			if _entries['type'] != 'searchResEntry':
				continue
			strip_entry(_entries)
			entries.append(_entries)
		return entries

	def get_domaindnsrecord(self, identity=None, zonename=None, properties=[], searchbase=None, args=None, search_scope=ldap3.SUBTREE, no_cache=False):
		def_prop = [
			'name',
			'distinguishedName',
			'dnsrecord',
			'whenCreated',
			'uSNChanged',
			'objectCategory',
			'objectGUID'
		]

		zonename = '*' if not zonename else zonename
		identity = escape_filter_chars(identity) if identity else None
		no_cache = args.no_cache if hasattr(args, 'no_cache') and args.no_cache else no_cache

		if not searchbase:
			searchbase = args.searchbase if hasattr(args, 'searchbase') and args.searchbase else f"CN=MicrosoftDNS,DC=DomainDnsZones,{self.root_dn}" 

		zones = self.get_domaindnszone(identity=zonename, properties=['distinguishedName'], searchbase=searchbase, no_cache=no_cache)
		if not zones:
			logging.error(f"[Get-DomainDNSRecord] Zone {zonename} not found")
			return

		entries = []
		identity_filter = ""
		if identity:
			identity_filter = f"(|(name={identity})(distinguishedName={identity}))"
		ldap_filter = f'(&(objectClass=dnsNode){identity_filter})'

		for zone in zones:
			logging.debug(f"[Get-DomainDNSRecord] Search base: {zone['attributes']['distinguishedName']}")
			logging.debug(f"[Get-DomainDNSRecord] LDAP Filter string: {ldap_filter}")
			entry_generator = self.ldap_session.extend.standard.paged_search(zone['attributes']['distinguishedName'], ldap_filter, attributes=def_prop, paged_size = 1000, generator=True, search_scope=search_scope, no_cache=no_cache)
			for _entries in entry_generator:
				if _entries['type'] != 'searchResEntry':
					continue
				strip_entry(_entries)
				for record in _entries['attributes']['dnsRecord']:
					if not isinstance(record, bytes):
						record = record.encode()
					dr = DNS_RECORD(record)
					_entries = modify_entry(_entries,new_attributes={
						'TTL': dr['TtlSeconds'],
						'TimeStamp': dr['TimeStamp'],
						'UpdatedAtSerial': dr['Serial'],
					})
					parsed_data = DNS_UTIL.parse_record_data(dr)
					if parsed_data:
						for data in parsed_data:
							_entries = modify_entry(_entries,new_attributes={
								data : parsed_data[data]
							})
					if properties:
						new_dict = filter_entry(_entries["attributes"], properties)
					else:
						new_dict = _entries["attributes"]

					entries.append({
						"attributes": new_dict
					})
		return entries

	def get_domainsccm(self, args=None, properties=[], identity=None, searchbase=None, search_scope=ldap3.SUBTREE):
		def_prop = [
			"cn",
			"distinguishedname",
			"instanceType",
			"name",
			"objectGUID",
			"dNSHostName",
			"mSSMSSiteCode",
			"mSSMSDefaultMP",
			"mSSMSMPName",
			"mSSMSDeviceManagementPoint",
			"mSSMSVersion",
			"mSSMSCapabilities",
		]
		properties = def_prop if not properties else properties
		identity = '*' if not identity else identity

		if not searchbase:
			searchbase = args.searchbase if hasattr(args, 'searchbase') and args.searchbase else self.root_dn 

		ldap_filter = ""
		identity_filter = f"(|(name={identity})(distinguishedName={identity}))"

		if args:
			if args.ldapfilter:
				logging.debug(f'[Get-DomainSCCM] Using additional LDAP filter: {args.ldapfilter}')
				ldap_filter += f'{args.ldapfilter}'

		ldap_filter = f'(&(objectClass=mSSMSManagementPoint){identity_filter}{ldap_filter})'

		logging.debug(f'[Get-DomainSCCM] LDAP search filter: {ldap_filter}')

		# in case need more then 1000 entries
		entries = []
		entry_generator = self.ldap_session.extend.standard.paged_search(searchbase, ldap_filter, attributes=properties, paged_size = 1000, generator=True, search_scope=search_scope)
		for _entries in entry_generator:
			if _entries['type'] != 'searchResEntry':
				continue
			strip_entry(_entries)
			entries.append(_entries)

		if args.check_datalib:
			if not entries:
				logging.info("[Get-DomainSCCM] No server found in domain. Skipping...")
				return entries

			target = entries['attributes']['dnsHostName']
			logging.debug("[Get-DomainSCCM] Verifying SCCM HTTP endpoint")

			sccm = SCCM(target)
			sccm.check_datalib_endpoint()
			
			if not sccm.http_enabled():
				logging.info("[Get-DomainSCCM] Failed to check with hostname, resolving dnsHostName attribute to IP and retrying...")
				target = host2ip(entries['attributes']['dnsHostName'], self.nameserver, 3, True, use_system_ns=self.use_system_nameserver)
				sccm.check_datalib_endpoint()

			entries = modify_entry(
				entries,
				new_attributes = {
					"DatalibEndpoint": sccm.http_enabled(),
					"DatalibEndpointAllowAnonymous": sccm.http_anonymous_enabled()
				}
			)

		return entries

	def get_domainsccmdatalib(self):
		entries = []
		if not sccm.http_enabled():
			logging.warning("[Get-DomainSCCM] Datalib endpoint not accessible. Skipping...")
			return entries

		# parse datalib
		logging.debug("[Get-DomainSCCMDatalib] Parsing SCCM Datalib HTTP endpoint")

		urls = sccm.parse_datalib(self.username, self.password)

		return entries

	def get_domainca(self, args=None, identity=None, check_web_enrollment=False, properties=None, search_scope=ldap3.SUBTREE):
		def_prop = [
			"cn",
			"name",
			"dNSHostName",
			"cACertificateDN",
			"cACertificate",
			"certificateTemplates",
			"objectGUID",
			"distinguishedName",
			"displayName",
		]
		properties = def_prop if not properties else properties
		check_web_enrollment = args.check_web_enrollment if hasattr(args, 'check_web_enrollment') else check_web_enrollment

		ca_fetch = CAEnum(self.ldap_session, self.root_dn)
		entries = ca_fetch.fetch_enrollment_services(properties, search_scope=search_scope)

		if check_web_enrollment:
			# check for web enrollment
			for i in range(len(entries)):
				# check if entries[i]['attributes']['dNSHostName'] is a list
				if isinstance(entries[i]['attributes']['dNSHostName'], list):
					target_name = entries[i]['attributes']['dNSHostName'][0]
				else:
					target_name = entries[i]['attributes']['dNSHostName']

				if not target_name:
					logging.warning(f"[Get-DomainCA] No DNS hostname found for {entries[i].get('dn')}")
					continue

				# resolve target name to IP
				target_ip = host2ip(target_name, self.nameserver, 3, True, use_system_ns=self.use_system_nameserver)

				web_enrollment = ca_fetch.check_web_enrollment(target_name)

				if not web_enrollment and (target_ip.casefold() != target_name.casefold()):
					logging.debug("[Get-DomainCA] Trying to check web enrollment with IP")
					web_enrollment = ca_fetch.check_web_enrollment(target_ip)

				entries[i] = modify_entry(
					entries[i],
					new_attributes = {
						"WebEnrollment": web_enrollment
					}
				)

		return entries

	def remove_domaincatemplate(self, identity, searchbase=None, args=None):
		if not searchbase:
			searchbase = args.searchbase if hasattr(args, 'searchbase') and args.searchbase else f"CN=Certificate Templates,CN=Public Key Services,CN=Services,CN=Configuration,{self.root_dn}"
		ca_fetch = CAEnum(self.ldap_session, self.root_dn)
		templates = ca_fetch.get_certificate_templates(identity=identity, ca_search_base=searchbase)
		if len(templates) > 1:
			logging.error(f"[Remove-DomainCATemplate] Multiple certificates found with name {identity}")
			return
		if len(templates) == 0:
			logging.error(f"[Remove-DomainCATemplate] Template {identity} not found in domain")
			return

		# delete operation
		# delete template from Certificate Templates
		# unissue the template
		cas = ca_fetch.fetch_enrollment_services()
		for ca in cas:
			if self.ldap_session.modify(ca["distinguishedName"].value, {'certificateTemplates':[(ldap3.MODIFY_DELETE,[templates[0]["name"].value])]}):
				logging.debug(f"[Remove-DomainCATemplate] Template {templates[0]['name'].value} is no longer issued")
			else:
				logging.warning(f"[Remove-DomainCATemplate] Failed to remove template from CA. Skipping...")
		
		# delete template oid
		oid = templates[0]["msPKI-Cert-Template-OID"].value
		template_oid = self.get_domainobject(identity_filter=f'(|(msPKI-Cert-Template-OID={oid}))',searchbase=f"CN=OID,CN=Public Key Services,CN=Services,CN=Configuration,{self.root_dn}", properties=['distinguishedName'])
		if len(template_oid) > 1:
			logging.error("[Remove-DomainCATemplate] Multiple OIDs found. Ignoring..")
		elif len(template_oid) == 0:
			logging.error("[Remove-DomainCATemplate] Template OID not found in domain. Ignoring...")

		oid_dn = template_oid[0]['attributes']['distinguishedName']
		logging.debug(f"[Remove-DomainCATemplate] Found template oid {oid_dn}")
		logging.debug(f"[Remove-DomainCATemplate] Deleting {oid_dn}")
		if self.ldap_session.delete(oid_dn):
			logging.debug(f"[Remove-DomainCATemplate] Template oid {oid} removed")
		else:
			logging.warning(f"[Remove-DomainCATemplate] Failed to remove template oid {oid}. Ignoring...")

		# delete template
		if self.ldap_session.delete(templates[0].entry_dn):
			logging.info(f"[Remove-DomainCATemplate] Success! {identity} template deleted")
			return True
		else:
			logging.error(self.ldap_session.result['message'] if self.args.debug else f"[Remove-DomainCATemplate] Failed to delete template {identity} from certificate store")
			return False

	def get_exchangeserver(self, identity, properties=[], searchbase=None, args=None, search_scope=ldap3.SUBTREE):
		if not searchbase:
			searchbase = args.searchbase if hasattr(args, 'searchbase') and args.searchbase else self.root_dn

		logging.debug(f"[Get-ExchangeServer] Using search base: {searchbase}")
		
		# query if Exchange Servers group exists
		exc_group = self.get_domaingroup(identity="Exchange Servers", searchbase=searchbase)

		if len(exc_group) == 0:
			logging.debug("[Get-ExchangeServer] Exchange Servers group not found in domain")
			return

		logging.debug("[Get-ExchangeServer] Exchange Servers group found in domain")
		exc_group_dn = exc_group[0].get("dn")
		if not exc_group_dn:
			logging.error("[Get-ExchangeServer] Failed to get Exchange Servers group dn")
			return

		exc_ldapfilter = "(memberOf=%s)" % (exc_group_dn)
		return self.get_domaincomputer(identity=identity, properties=properties, searchbase=searchbase, ldapfilter=exc_ldapfilter, search_scope=search_scope)

	def unlock_adaccount(self, identity, searchbase=None, args=None):
		if not searchbase:
			searchbase = args.searchbase if hasattr(args, 'searchbase') and args.searchbase else self.root_dn
		
		# check if identity exists
		identity_object = self.get_domainobject(identity=identity, searchbase=searchbase, properties=["distinguishedName","sAMAccountName","lockoutTime"])
		if len(identity_object) > 1:
			logging.error(f"[Unlock-ADAccount] More then one identity found. Use distinguishedName instead.")
			return False
		elif len(identity_object) == 0:
			logging.error(f"[Unlock-ADAccount] Identity {identity} not found in domain")
			return False

		# check if its really locked
		identity_dn = identity_object[0].get("dn")
		identity_san = identity_object[0].get("attributes").get("sAMAccountName")
		identity_lockouttime = identity_object[0].get("raw_attributes").get("lockoutTime")

		logging.debug(f"[Unlock-ADAccount] Identity {identity_san} found in domain")
		
		if isinstance(identity_lockouttime, list):
			identity_lockouttime = identity_lockouttime[0]
		locked = int(identity_lockouttime)

		if not locked or locked == 0:
			logging.warning(f"[Unlock-ADAccount] Account {identity_san} is not in locked state.")
			return False

		logging.debug("[Unlock-ADAccount] Modifying lockoutTime attribute")
		succeed = self.set_domainobject(  
								identity_dn,
								_set = {
										'attribute': 'lockoutTime',
										'value': '0'
									},
							  )

		if succeed:
			logging.info(f"[Unlock-ADAccount] Account {identity_san} unlocked")
			return True
		else:
			logging.info(f"[Unlock-ADAccount] Failed to unlock {identity_san}")
			return False

	def add_domaingpo(self, identity, description=None, basedn=None, args=None):
		name = '{%s}' % get_uuid(upper=True)

		basedn = "CN=Policies,CN=System,%s" % (self.root_dn) if not basedn else basedn
		dn_exist = self.get_domainobject(identity=basedn)
		if not dn_exist:
			logging.error(f"[Add-DomainGPO] DN {basedn} not found in domain")
			return False

		# adding new folder policy folder in sysvol share
		dc = None
		dcs = self.get_domaincontroller(properties=['dnsHostName'])
		if len(dcs) == 0:
			logging.warning("[Add-DomainGPO] No domain controller found in ldap. Using domain as address")
		elif dcs[0].get("attributes").get("dnsHostName"):
			logging.debug("[Add-DomainGPO] Found %d domain controller(s). Using the first one" % len(dcs))
			dc = dcs[0].get("attributes").get("dnsHostName")

		if not dc:
			dc = self.domain
		
		logging.debug("[Add-DomainGPO] Resolving hostname to IP")
		dc = host2ip(dc, self.nameserver, 3, True, use_system_ns=self.use_system_nameserver)

		share = "SYSVOL"
		policy_path = "/%s/Policies/%s" % (
			self.domain,
			name
		)
		smbconn = self.conn.init_smb_session(dc)
		try:
			tid = smbconn.connectTree(share)
		except Exception as e:
			logging.error("[Add-DomainGPO] Failed to connect to SYSVOL share")
			return False

		try:
			logging.debug("[Add-DomainGPO] Creating directories in %s" % (policy_path))
			smbconn.createDirectory(share, policy_path)
			smbconn.createDirectory(share, policy_path + "/Machine")
			smbconn.createDirectory(share, policy_path + "/User")
		except Exception as e:
			logging.error("[Add-DomainGPO] Failed to create policy directory in SYSVOL")
			logging.error(str(e))
			return False

		logging.debug("[Add-DomainGPO] Writing default GPT.INI file")
		gpt_ini_content = """[General]
Version=0
displayName=New Group Policy Object

"""
		try:
			fid = smbconn.createFile(tid, policy_path + "/GPT.ini")
		except Exception as e:
			logging.error("[Add-DomainGPO] Failed to create gpt.ini file in %s" % (policy_path))
			return False
		try:
			smbconn.writeFile(tid, fid, gpt_ini_content)
		except Exception as e:
			logging.error("[Add-DomainGPO] Failed to write gpt.ini file in %s" % (policy_path))
			return False

		smbconn.closeFile(tid, fid)
		logging.info("[Add-DomainGPO] SYSVOL policy folder successfully created!")

		dn = "CN=%s,%s" % (name, basedn)
		logging.debug(f"[Add-DomainGPO] Adding GPO with dn: {dn}")

		gpo_data = {
			'displayName':identity,
			'name': name,
			'gPCFunctionalityVersion': 2,
			'gPCFileSysPath': "\\\\%s\\SysVol%s" % (self.domain, policy_path.replace("/","\\"))
		}

		self.ldap_session.add(dn, ['top','container','groupPolicyContainer'], gpo_data)

		# adding new gplink
		if args.linkto is not None:
			self.add_gplink(guid=name, targetidentity=args.linkto)

		if self.ldap_session.result['result'] == 0:
			logging.info(f"[Add-DomainGPO] Added new {identity} GPO object")
			return True
		else:
			logging.error(f"[Add-DomainGPO] Failed to create {identity} GPO ({self.ldap_session.result['description']})")
			return False

	def add_domainou(self, identity, basedn=None, args=None):
		basedn = self.root_dn if not basedn else basedn

		dn_exist = self.get_domainobject(identity=basedn)
		if not dn_exist:
			logging.error(f"[Add-DomainOU] DN {basedn} not found in domain")
			return False

		dn = "OU=%s,%s" % (identity, basedn)
		logging.debug(f"[Add-DomainOU] OU distinguishedName: {dn}")

		
		ou_data = {
				'objectCategory': 'CN=Organizational-Unit,CN=Schema,CN=Configuration,%s' % self.root_dn,
				'name': identity,
				}

		self.ldap_session.add(dn, ['top','organizationalUnit'], ou_data)
		
		if args.protectedfromaccidentaldeletion:
			logging.info("[Add-DomainOU] Protect accidental deletion enabled")
			self.add_domainobjectacl(identity, "Everyone", rights="immutable", ace_type="denied")
		
		if self.ldap_session.result['result'] == 0:
			logging.info(f"[Add-DomainOU] Added new {identity} OU")
			return True
		else:
			logging.error(f"[Add-DomainOU] Failed to create {identity} OU ({self.ldap_session.result['description']})")
			return False

	def remove_domainou(self, identity, searchbase=None, sd_flag=None, args=None):
		if not searchbase:
			searchbase = args.searchbase if hasattr(args, 'searchbase') and args.searchbase else self.root_dn

		# verify if the ou exists
		targetobject = self.get_domainobject(identity=identity, searchbase=searchbase, properties=['distinguishedName'], sd_flag=sd_flag)
		if len(targetobject) > 1:
			logging.error(f"[Remove-DomainOU] More than one object found")
			return False
		elif len(targetobject) == 0:
			logging.error(f"[Remove-DomainOU] {identity} not found in domain")
			return False

		# set the object new dn
		if isinstance(targetobject, list):
			targetobject_dn = targetobject[0]["attributes"]["distinguishedName"]
		else:
			targetobject_dn = targetobject["attributes"]["distinguishedName"]

		logging.debug(f"[Remove-DomainOU] Removing {targetobject_dn}")

		succeeded = self.ldap_session.delete(targetobject_dn)

		if not succeeded:
			logging.error(f"[Remove-DomainOU] Failed to delete OU ({self.ldap_session.result['message']})")
			return False
		else:
			logging.info("[Remove-DomainOU] Success! Deleted the OU")
			return True

	def remove_gplink(self, guid, targetidentity, searchbase=None, sd_flag=None, args=None):
		if not searchbase:
			searchbase = args.searchbase if hasattr(args, 'searchbase') and args.searchbase else self.root_dn

		# verify that the gpidentity exists
		gpo = self.get_domaingpo(identity=guid, properties=[
			'name',
			'distinguishedName',
			],
			searchbase=searchbase,
		)
		if len(gpo) > 1:
			logging.error("[Remove-GPLink] More than one GPO found")
			return
		elif len(gpo) == 0:
			logging.error("[Remove-GPLink] GPO not found in domain")
			return

		if isinstance(gpo, list):
			gpidentity = gpo[0]["attributes"]["distinguishedName"]
		else:
			gpidentity = gpo["attributes"]["distinguishedName"]

		logging.debug(f"[Remove-GPLink] Found GPO with GUID {gpidentity}")

		# verify that the target identity exists
		target_identity = self.get_domainobject(identity=targetidentity, properties=[
			'*',
			],
			searchbase=searchbase,
			sd_flag=sd_flag
			)
		if len(target_identity) > 1:
			logging.error("[Remove-GPLink] More than one principal identity found")
			return
		elif len(target_identity) == 0:
			logging.error("[Remove-GPLink] Principal identity not found in domain")
			return

		if isinstance(target_identity, list):
			targetidentity_dn = target_identity[0]["attributes"]["distinguishedName"]
			targetidentity_gplink = target_identity[0]["attributes"].get("gPLink")
		else:
			targetidentity_dn = target_identity["attributes"]["distinguishedName"]
			targetidentity_gplink = target_identity["attributes"].get("gPLink")

		logging.debug(f"[Remove-GPLink] Found target identity {targetidentity_dn}")

		if not targetidentity_gplink:
			logging.error("[Remove-GPLink] Principal identity doesn't have any linked GPO")
			return

		# parsing gPLink attribute and remove selected gpo
		pattern = r"(?<=\[).*?(?=\])"
		new_gplink = ""
		gplinks = re.findall(pattern, targetidentity_gplink)
		for link in gplinks:
			if guid.lower() not in link.lower():
				new_gplink += "[%s]" % (link)
		
		if new_gplink:
			succeed = self.set_domainobject(  
									targetidentity_dn,
									_set = {
											'attribute': 'gPLink',
											'value': [new_gplink]
										},
								  )
		else:
			succeed = self.set_domainobject(  
									targetidentity_dn,
									clear = "gPLink"
								  )

		if succeed:
			logging.info(f"[Remove-GPLink] Successfully modified gPLink on {targetidentity_dn} OU")
			return True
		else:
			logging.error(f"[Remove-GPLink] Failed to modify gPLink on {targetidentity_dn} OU")
			return False

	def add_gplink(self, guid, targetidentity, link_enabled="Yes", enforced="No", searchbase=None, sd_flag=None, args=None):
		if not searchbase:
			searchbase = args.searchbase if hasattr(args, 'searchbase') and args.searchbase else self.root_dn

		# verify that the gpidentity exists
		gpo = self.get_domaingpo(identity=guid, properties=[
			'name',
			'distinguishedName',
			],
			searchbase=searchbase,
		)
		if len(gpo) > 1:
			logging.error("[Add-GPLink] More than one GPO found")
			return
		elif len(gpo) == 0:
			logging.error("[Add-GPLink] GPO not found in domain")
			return

		if isinstance(gpo, list):
			gpidentity_dn = gpo[0]["attributes"]["distinguishedName"]
		else:
			gpidentity_dn = gpo["attributes"]["distinguishedName"]

		logging.debug(f"[Add-GPLink] Found GPO with GUID {gpidentity_dn}")

		# verify that the target identity exists
		target_identity = self.get_domainobject(identity=targetidentity, properties=[
			'*',
			],
			searchbase=searchbase,
			sd_flag=sd_flag
			)
		if len(target_identity) > 1:
			logging.error("[Add-GPLink] More than one principal identity found")
			return
		elif len(target_identity) == 0:
			logging.error("[Add-GPLink] Principal identity not found in domain")
			return

		if isinstance(target_identity, list):
			targetidentity_dn = target_identity[0]["attributes"]["distinguishedName"]
			targetidentity_gplink = target_identity[0]["attributes"].get("gPLink")
		else:
			targetidentity_dn = target_identity["attributes"]["distinguishedName"]
			targetidentity_gplink = target_identity["attributes"].get("gPLink")

		logging.debug(f"[Add-GPLink] Found target identity {targetidentity_dn}")
		
		logging.warning(f"[Add-GPLink] Adding new GPLink to {targetidentity_dn}")

		attr = "0"
		if enforced.casefold() == "Yes".casefold():
			if link_enabled.casefold() == "Yes".casefold():
				attr = "2"
			elif link_enabled.casefold() == "No".casefold():
				attr = "3"
		elif enforced.casefold() == "No".casefold():
			if link_enabled.casefold() == "Yes".casefold():
				attr = "0"
			elif link_enabled.casefold() == "No".casefold():
				attr = "1"

		gpidentity = "[LDAP://%s;%s]" % (gpidentity_dn, attr)

		if targetidentity_gplink:
			if gpidentity_dn in targetidentity_gplink:
				logging.error("[Add-GPLink] gPLink attribute already exists")
				return

			logging.debug("[Add-GPLink] gPLink attribute already populated. Appending new gPLink...")
			targetidentity_gplink += gpidentity
		else:
			targetidentity_gplink = gpidentity

		if self.args.debug:
			logging.debug(f"[Add-GPLink] gPLink value: {gpidentity}")

		succeed = self.set_domainobject(  
								targetidentity_dn,
								_set = {
										'attribute': 'gPLink',
										'value': [targetidentity_gplink]
									},
							  )

		if succeed:
			logging.info(f"[Add-GPLink] Successfully added gPLink to {targetidentity_dn} OU")
			return True
		else:
			logging.error(f"[Add-GPLink] Failed to add gPLink to {targetidentity_dn} OU")
			return False

	def add_domaincatemplateacl(self, name, principalidentity, rights=None, ca_fetch=None, args=None):
		if not rights:
			if args and hasattr(args, 'rights') and args.rights:
				rights = args.rights
		else:
			rights = 'all'

		principal_identity = self.get_domainobject(identity=principalidentity, properties=[
			'objectSid',
			'distinguishedName',
			'sAMAccountName'
		])
		if len(principal_identity) > 1:
			logging.error("[Add-DomainCATemplateAcl] More than one target identity found")
			return
		elif len(principal_identity) == 0:
			logging.error("[Add-DomainCATemplateAcl] Target identity not found in domain")
			return

		logging.debug(f"[Add-DomainCATemplateAcl] Found target identity {principal_identity[0].get('attributes').get('sAMAccountName')}")

		if not ca_fetch:
			ca_fetch = CAEnum(self.ldap_session, self.root_dn)

		template = ca_fetch.get_certificate_templates(identity=name)
		
		if len(template) == 0:
			logging.error(f"[Add-DomainCATemplateAcl] {name} template not found in domain")
			return
		elif len(template) > 1:
			logging.error("[Add-DomainCATemplateAcl] Multiple templates found")
			return

		logging.debug(f"[Add-DomainCATemplateAcle] Template {name} exists")

		template_parser = PARSE_TEMPLATE(template[0],current_user_sid=self.current_user_sid,ldap_session = self.ldap_session)
		secDesc = template_parser.modify_dacl(principal_identity[0].get('attributes').get('objectSid'), rights)
		succeed = self.set_domainobject(  
								name,
								_set = {
										'attribute': 'nTSecurityDescriptor',
										'value': [secDesc]
									},
								searchbase=f"CN=Certificate Templates,CN=Public Key Services,CN=Services,CN=Configuration,{self.root_dn}",
								sd_flag = 0x04
							  )
		if succeed:
			logging.info(f"[Add-DomainCATemplateAcl] Successfully modified {name} template acl")
			return True
		else:
			logging.error(f"[Add-DomainCATemplateAcl] Failed to modify {name} template ACL")
			return False

	def add_domaincatemplate(self, displayname, name=None, args=None):
		ca_fetch = CAEnum(self.ldap_session, self.root_dn)

		if not name:
			logging.debug("[Add-DomainCATemplate] No certificate name given, using DisplayName instead")
			name = displayname.replace(" ","").strip()

		# check if template exists
		ex_templates = ca_fetch.get_certificate_templates(identity=name)
		if len(ex_templates) > 0:
			logging.error(f"[Add-DomainCATemplate] Template {name} already exists")
			return

		if args.duplicate:
			# query for other cert template
			identity = args.duplicate
			entries = ca_fetch.get_certificate_templates(identity=identity, properties=['*'])
			if len(entries) > 1:
				logging.error("[Add-DomainCATemplate] More than one certificate templates found")
				return False
			elif len(entries) == 0:
				logging.error("[Add-DomainCATemplate] No certificate template found")
				return False

			logging.info(f"[Add-DomainCATemplate] Duplicating existing template {args.duplicate} properties")
			default_template = {
				'DisplayName': displayname,
				'name': name,
				'msPKI-Certificate-Name-Flag' : int(entries[0]['msPKI-Certificate-Name-Flag'].value) if entries[0]['msPKI-Certificate-Name-Flag'] else 1,
				'msPKI-Enrollment-Flag': int(entries[0]['msPKI-Enrollment-Flag'].value) if entries[0]['msPKI-Enrollment-Flag'] else 41,
				'revision': int(entries[0]['revision'].value) if entries[0]['revision'] else 3,
				'pKIDefaultKeySpec': int(entries[0]['pKIDefaultKeySpec'].value) if entries[0]['pKIDefaultKeySpec'] else 1,
				'msPKI-RA-Signature': int(entries[0]['msPKI-RA-Signature'].value) if entries[0]['msPKI-RA-Signature'] else 0,
				'pKIMaxIssuingDepth': int(entries[0]['pKIMaxIssuingDepth'].value) if entries[0]['pKIMaxIssuingDepth'] else 0,
				'msPKI-Template-Schema-Version': int(entries[0]['msPKI-Template-Schema-Version'].value) if entries[0]['msPKI-Template-Schema-Version'] else 1,
				'msPKI-Template-Minor-Revision': int(entries[0]['msPKI-Template-Minor-Revision'].value) if entries[0]['msPKI-Template-Minor-Revision'] else 1,
				'msPKI-Private-Key-Flag': int(entries[0]['msPKI-Private-Key-Flag'].value) if entries[0]['msPKI-Private-Key-Flag'] else 16842768,
				'msPKI-Minimal-Key-Size': int(entries[0]['msPKI-Minimal-Key-Size'].value) if entries[0]['msPKI-Minimal-Key-Size'] else 2048,
				"pKICriticalExtensions": entries[0]['pKICriticalExtensions'].values if entries[0]['pKICriticalExtensions'] else ["2.5.29.19", "2.5.29.15"],
				"pKIExtendedKeyUsage": entries[0]['pKIExtendedKeyUsage'].values if entries[0]['pKIExtendedKeyUsage'] else ["1.3.6.1.4.1.311.10.3.4","1.3.6.1.5.5.7.3.4","1.3.6.1.5.5.7.3.2"],
				'nTSecurityDescriptor': entries[0]['nTSecurityDescriptor'].raw_values[0],
				"pKIExpirationPeriod": entries[0]['pKIExpirationPeriod'].raw_values[0],
				"pKIOverlapPeriod": entries[0]['pKIOverlapPeriod'].raw_values[0],
				"pKIDefaultCSPs": entries[0]['pKIDefaultCSPs'].value if entries[0]['pKIDefaultCSPs'] else b"1,Microsoft Enhanced Cryptographic Provider v1.0",
			}
		else:
			default_template = {
				'DisplayName': displayname,
				'name': name,
				'msPKI-Certificate-Name-Flag' : 1,
				'msPKI-Enrollment-Flag': 41,
				'revision': 3,
				'pKIDefaultKeySpec': 1,
				'msPKI-RA-Signature': 0,
				'pKIMaxIssuingDepth': 0,
				'msPKI-Template-Schema-Version': 1,
				'msPKI-Template-Minor-Revision': 1,
				'msPKI-Private-Key-Flag': 16842768,
				'msPKI-Minimal-Key-Size': 2048,
				"pKICriticalExtensions": ["2.5.29.19", "2.5.29.15"],
				"pKIExtendedKeyUsage": [
					"1.3.6.1.4.1.311.10.3.4",
					"1.3.6.1.5.5.7.3.4",
					"1.3.6.1.5.5.7.3.2"
				],
				"pKIExpirationPeriod": b"\x00@\x1e\xa4\xe8e\xfa\xff",
				"pKIOverlapPeriod": b"\x00\x80\xa6\n\xff\xde\xff\xff",
				"pKIDefaultCSPs": b"1,M#icrosoft Enhanced Cryptographic Provider v1.0",
			}

		# create certiciate template
		# create oid
		basedn = f"CN=OID,CN=Public Key Services,CN=Services,CN=Configuration,{self.root_dn}"
		self.ldap_session.search(basedn, "(objectclass=*)" ,attributes=['msPKI-Cert-Template-OID'])

		if len(self.ldap_session.entries) == 0:
			logging.error("[Add-DomainCATemplate] No Forest OID found in domain")

		forest_oid = self.ldap_session.entries[0]['msPKI-Cert-Template-OID'].value
		template_oid, template_name = UTILS.get_template_oid(forest_oid)
		oa = {
				'Name': template_name,
				'DisplayName': displayname,
				'flags' : 0x01,
				'msPKI-Cert-Template-OID': template_oid,
				}
		oidpath = f"CN={template_name},CN=OID,CN=Public Key Services,CN=Services,CN=Configuration,{self.root_dn}"
		self.ldap_session.add(oidpath, ['top','msPKI-Enterprise-Oid'], oa)
		if self.ldap_session.result['result'] == 0:
			logging.debug(f"[Add-DomainCATemplate] Added new template OID {oidpath}")
			logging.debug(f"[Add-DomainCATemplate] msPKI-Cert-Template-OID: {template_oid}")
			default_template['msPKI-Cert-Template-OID'] = template_oid
		else:
			logging.error(f"[Add-DomainCATemplate] Error adding new template OID ({self.ldap_session.result['description']})")
			return False

		template_base = f"CN={name},CN=Certificate Templates,CN=Public Key Services,CN=Services,CN=Configuration,{self.root_dn}"
		self.ldap_session.add(template_base, ['top','pKICertificateTemplate'], default_template)
		if self.ldap_session.result['result'] == 0:
			logging.info(f"[Add-DomainCATemplate] Added new certificate template {name}")
		else:
			logging.error(f"[Add-DomainCATemplate] Failed to create certiciate template {name} ({self.ldap_session.result['description']})")
			return False

		# set acl for the template
		if not args.duplicate:
			cur_user = self.conn.who_am_i().split('\\')[1]
			logging.debug("[Add-DomainCATemplate] Modifying template ACL for current user")
			if not self.add_domaincatemplateacl(name,cur_user,ca_fetch=ca_fetch):
				logging.debug("[Add-DomainCATemplate] Failed to modify template ACL. Skipping...")

		# issue certificate
		cas = ca_fetch.fetch_enrollment_services()
		for ca in cas:
			ca_dn = ca['distinguishedName'].value
			ca_name = ca['name'].value
			logging.debug(f"[Add-DomainCATemplate] Issuing certificate template to {ca_name}")
			succeed = self.set_domainobject(
						ca_name,
						append={
							'attribute': 'certificateTemplates',
							'value': [name]
						},
						searchbase = ca_dn
					)

			if succeed:
				logging.info(f"[Add-DomainCATemplate] Template {name} issued!")
			else:
				logging.error("[Add-DomainCATemplate] Failed to issue template")

		return succeed

	def get_domaincatemplate(self, args=None, properties=[], identity=None, vulnerable=False, searchbase=None, resolve_sids=False):
		def list_sids(sids: List[str]):
			sids_mapping = list(
				map(
					lambda sid: repr(self.convertfrom_sid(sid)),
					sids,
				)
			)
			if len(sids_mapping) == 1:
				return sids_mapping[0]

			return ", ".join(sids_mapping[:-1]) + " and " + sids_mapping[-1]

		def_prop = [
			"objectClass",
			"cn",
			"distinguishedName",
			"name",
			"displayName",
			"pKIExpirationPeriod",
			"pKIOverlapPeriod",
			"msPKI-Enrollment-Flag",
			"msPKI-Private-Key-Flag",
			"msPKI-Certificate-Name-Flag",
			"msPKI-Cert-Template-OID",
			"msPKI-RA-Signature",
			"pKIExtendedKeyUsage",
			"nTSecurityDescriptor",
			"objectGUID",
			"msPKI-Template-Schema-Version",
			"msPKI-Certificate-Policy",
			"msPKI-Minimal-Key-Size"
		]

		identity = '*' if not identity else identity
		if not searchbase:
			searchbase = args.searchbase if hasattr(args, 'searchbase') and args.searchbase else f"CN=Certificate Templates,CN=Public Key Services,CN=Services,CN=Configuration,{self.root_dn}"
		resolve_sids = args.resolve_sids if hasattr(args, 'resolve_sids') and args.resolve_sids else resolve_sids
		args_enabled = args.enabled if hasattr(args, 'enabled') and args.enabled else False
		args_vulnerable = args.vulnerable if hasattr(args, 'vulnerable') and args.vulnerable else vulnerable

		entries = []
		template_guids = []
		ca_fetch = CAEnum(self.ldap_session, self.root_dn)

		templates = ca_fetch.get_certificate_templates(def_prop,searchbase,identity)
		cas = ca_fetch.fetch_enrollment_services()

		if len(cas) <= 0:
			logging.error(f"[Get-DomainCATemplate] No certificate authority found")
			return

		logging.debug(f"[Get-DomainCATemplate] Found {len(cas)} CA(s)")
		# Entries only
		list_ca_templates = []
		list_entries = []

		# Get issuance policies for each template
		oids = ca_fetch.get_issuance_policies()
		for ca in cas:
			list_ca_templates += ca.get('attributes').get('certificateTemplates')
			for template in templates:
				#template = template.entry_writable()
				vulnerable = False
				vulns = {}
				list_vuln = []

				# avoid dupes
				if template["objectGUID"] in template_guids:
					continue
				else:
					template_guids.append(template["objectGUID"])

				# Oid
				object_id = template["objectGUID"].value.lstrip("{").rstrip("}")
				issuance_policies = template["msPKI-Certificate-Policy"].value

				if not isinstance(issuance_policies, list):
					if issuance_policies is None:
						issuance_policies = []
					else:
						issuance_policies = [issuance_policies]

				linked_group = None
				for oid in oids:
					if oid["attributes"].get("msPKI-Cert-Template-OID") in issuance_policies:
						linked_group = oid["attributes"].get("msDS-OIDToGroupLink")


				# get enrollment rights
				template_ops = PARSE_TEMPLATE(template, current_user_sid=self.current_user_sid, linked_group=linked_group, ldap_session=self.ldap_session)
				parsed_dacl = template_ops.parse_dacl()
				template_ops.resolve_flags()
				template_owner = template_ops.get_owner_sid()
				certificate_name_flag = template_ops.get_certificate_name_flag()
				enrollment_flag = template_ops.get_enrollment_flag()
				# print(enrollment_flag)
				extended_key_usage = template_ops.get_extended_key_usage()
				validity_period = template_ops.get_validity_period()
				renewal_period = template_ops.get_renewal_period()
				requires_manager_approval = template_ops.get_requires_manager_approval()

				vulns = template_ops.check_vulnerable_template()

				if resolve_sids:
					template_owner = self.convertfrom_sid(template_ops.get_owner_sid())

					for i in range(len(parsed_dacl['Extended Rights'])):
						try:
							parsed_dacl['Extended Rights'][i] = self.convertfrom_sid(parsed_dacl['Extended Rights'][i])
						except:
							pass

					for i in range(len(parsed_dacl['Enrollment Rights'])):
						try:
							parsed_dacl['Enrollment Rights'][i] = self.convertfrom_sid(parsed_dacl['Enrollment Rights'][i])
						except:
							pass

					for k in range(len(parsed_dacl['Write Owner'])):
						try:
							parsed_dacl['Write Owner'][k] = self.convertfrom_sid(parsed_dacl['Write Owner'][k])
						except:
							pass

					for j in range(len(parsed_dacl['Write Dacl'])):
						try:
							parsed_dacl['Write Dacl'][j] = self.convertfrom_sid(parsed_dacl['Write Dacl'][j])
						except:
							pass

					for y in range(len(parsed_dacl['Write Property'])):
						try:
							parsed_dacl['Write Property'][y] = self.convertfrom_sid(parsed_dacl['Write Property'][y])
						except:
							pass

					# Resolve Vulnerable (With resolvesids)
					for y in vulns.keys():
						try:
							list_vuln.append(y+" - "+list_sids(vulns[y]))
						except:
							list_vuln.append(vulns[y])

				# Resolve Vulnerable (Without resolvesids)
				if not resolve_sids:
					for y in vulns.keys():
						try:
							list_vuln.append(y+" - "+vulns[y])
						except:
							list_vuln.append(vulns[y])

				e = modify_entry(template,
								 new_attributes={
									'Owner': template_owner,
									'Certificate Authorities': ca.get('attributes').get('name'),
									'msPKI-Certificate-Name-Flag': certificate_name_flag,
									'msPKI-Enrollment-Flag': enrollment_flag,
									'pKIExtendedKeyUsage': extended_key_usage,
									'pKIExpirationPeriod': validity_period,
									'pKIOverlapPeriod': renewal_period,
									'ManagerApproval': requires_manager_approval,
									'Enrollment Rights': parsed_dacl['Enrollment Rights'],
									'Extended Rights': parsed_dacl['Extended Rights'],
									'Client Authentication': template_ops.get_client_authentication(),
									'Enrollment Agent': template_ops.get_enrollment_agent(),
									'Any Purpose': template_ops.get_any_purpose(),
									**({"Linked Groups": linked_group} if linked_group is not None else {}),
									'Write Owner': parsed_dacl['Write Owner'],
									'Write Dacl': parsed_dacl['Write Dacl'],
									'Write Property': parsed_dacl['Write Property'],
									'Enabled': False,
									'Vulnerable': list_vuln
									
									# 'Vulnerable': ",\n".join([i+" - "+vulns[i] for i in vulns.keys()]),
									#'Description': vulns['ESC1']
								},
								 remove = [
									 'nTSecurityDescriptor',
									 'msPKI-Certificate-Name-Flag',
									 'msPKI-Enrollment-Flag',
									 'pKIExpirationPeriod',
									 'pKIOverlapPeriod',
									 'pKIExtendedKeyUsage'
								 ]
								 )
				new_dict = e["attributes"]
				list_entries.append(new_dict)

		# Enabled + Vulnerable only
		for ent in list_entries:
			# Enabled
			enabled = False
			if ent["cn"][0] in list_ca_templates:
				enabled = True
				ent["Enabled"] = enabled

			if args_enabled and not enabled:
				continue

			# Vulnerable
			vulnerable = False
			if ent["Vulnerable"]:
				vulnerable = True

			if args_vulnerable and not vulnerable:
				continue

			if properties:
				ent = filter_entry(ent,properties)

			entries.append({
				"attributes": ent
			})

		template_guids.clear()
		return entries

	def set_domainrbcd(self, identity, delegatefrom, searchbase=None, args=None):
		if not searchbase:
			searchbase = args.searchbase if hasattr(args, 'searchbase') and args.searchbase else self.root_dn

		# verify that the identity exists
		_identity = self.get_domainobject(identity=identity, properties = [
			"sAMAccountName",
			"objectSid",
			"distinguishedName",
			"msDS-AllowedToActOnBehalfOfOtherIdentity"
			],
			searchbase=searchbase,
			sd_flag=0x01
		)

		if len(_identity) > 1:
			logging.error("[Set-DomainRBCD] More then one identity found")
			return
		elif len(_identity) == 0:
			logging.error(f"[Set-DomainRBCD] {identity} identity not found in domain")
			return
		
		logging.debug(f"[Set-DomainRBCD] {identity} identity found")
		targetidentity = _identity[0]

		# verify that delegate identity exists
		delegfrom_identity = self.get_domainobject(identity=delegatefrom, properties = [
				"sAMAccountName",
				"objectSid",
				"distinguishedName",
			],
			searchbase=searchbase
		)

		if len(delegfrom_identity) > 1:
			logging.error("[Set-DomainRBCD] More then one identity found")
			return False
		elif len(delegfrom_identity) == 0:
			logging.error(f"[Set-DomainRBCD] {delegatefrom} identity not found in domain")
			return False
		logging.debug(f"[Set-DomainRBCD] {delegatefrom} identity found")

		# now time to modify
		delegfrom_identity = delegfrom_identity[0]
		delegfrom_sid = delegfrom_identity.get("attributes").get("objectSid")

		if delegfrom_sid is None:
			return False

		rbcd = RBCD(targetidentity, self.ldap_session)
		succeed = rbcd.write_to(delegfrom_sid)
		if succeed:
			logging.info(f"[Set-DomainRBCD] Success! {delegatefrom} is now in {identity}'s msDS-AllowedToActOnBehalfOfOtherIdentity attribute")
		else:
			logging.error("[Set-DomainRBCD] Failed to write to {delegatefrom} object")
			return False

		return True

	def set_domainobjectowner(self, targetidentity, principalidentity, searchbase=None, args=None):
		"""
		Change the owner of a domain object to a new principal identity in the LDAP directory.

		Parameters:
			targetidentity: Identity of the object whose ownership is to be changed.
			principalidentity: Identity of the new owner.
			searchbase: Optional. The search base for looking up the target identity.
			args: Additional arguments, mainly used to determine the search base if not provided.

		Returns:
		bool: True if successful, False otherwise.
		"""
		if not searchbase:
			searchbase = args.searchbase if hasattr(args, 'searchbase') and args.searchbase else self.root_dn
		
		# verify that the targetidentity exists
		target_identity = self.get_domainobject(identity=targetidentity, properties=[
			'nTSecurityDescriptor',
			'sAMAccountname',
			'ObjectSID',
			'distinguishedName',
			],
			searchbase=searchbase,
			sd_flag=0x01,
		)
		if len(target_identity) > 1:
			logging.error("[Set-DomainObjectOwner] More than one target identity found")
			return False
		elif len(target_identity) == 0:
			logging.error(f"[Set-DomainObjectOwner] {targetidentity} identity not found in domain")
			return False
		logging.debug(f"[Set-DomainObjectOwner] {targetidentity} identity found")

		# verify that the principalidentity exists
		principal_identity = self.get_domainobject(identity=principalidentity)
		if len(principal_identity) > 1:
			logging.error("[Set-DomainObjectOwner] More than one principal identity found")
			return False
		elif len(principal_identity) == 0:
			logging.error(f"[Set-DomainObjectOwner] {principalidentity} identity not found in domain")
			return False
		logging.debug(f"[Set-DomainObjectOwner] {principalidentity} identity found")

		# create changeowner object
		chown = ObjectOwner(target_identity[0])
		target_identity_owner = chown.read()

		if target_identity_owner == principal_identity[0]["attributes"]["objectSid"]:
			logging.warning("[Set-DomainObjectOwner] %s is already the owner of the %s" % (principal_identity[0]["attributes"]["sAMAccountName"], target_identity[0]["attributes"]["distinguishedName"]))
			return False

		logging.info("[Set-DomainObjectOwner] Changing current owner %s to %s" % (target_identity_owner, principal_identity[0]["attributes"]["objectSid"]))

		new_secdesc = chown.modify_securitydescriptor(principal_identity[0])

		succeeded = self.ldap_session.modify(
			target_identity[0]["attributes"]["distinguishedName"],
			{'nTSecurityDescriptor': (ldap3.MODIFY_REPLACE, [
				new_secdesc.getData()
			])},
			controls=security_descriptor_control(sdflags=0x01)
		)

		if not succeeded:
			logging.error(f"[Set-DomainObjectOwner] Error modifying object owner ({self.ldap_session.result['description']})")
			return False
		else:
			logging.info(f'[Set-DomainObjectOwner] Success! modified owner for {target_identity[0]["attributes"]["distinguishedName"]}')

		return succeeded

	def set_domaincatemplate(self, identity, args=None):
		if not args or not identity:
			logging.error("[Set-DomainCATemplate] No identity or args supplied")
			return

		ca_fetch = CAEnum(self.ldap_session, self.root_dn)
		target_template = ca_fetch.get_certificate_templates(identity=identity, properties=['*'])
		if len(target_template) == 0:
			logging.error("[Set-DomainCATemplate] No template found")
			return False
		elif len(target_template) > 1:
			logging.error('[Set-DomainCATemplate] More than one template found')
			return False
		logging.info(f'[Set-DomainCATempalte] Found template dn {target_template[0].entry_dn}')

		attr_key = ""
		attr_val = []

		if args.clear:
			attr_key = args.clear
		else:
			attrs = ini_to_dict(args.set) if args.set else ini_to_dict(args.append)

			if not attrs:
				logging.error(f"Parsing {'-Set' if args.set else '-Append'} value failed")
				return

			try:
				for val in attrs['value']:
					try:
						if val in target_template[0][attrs['attribute']]:
							logging.error(f"[Set-DomainCATemplate] Value {val} already set in the attribute "+attrs['attribute'])
							return
					except KeyError as e:
						logging.debug("[Set-DomainCATemplate] Attribute %s not found in template" % attrs['attribute'])
			except ldap3.core.exceptions.LDAPKeyError as e:
				logging.error(f"[Set-DomainCATemplate] Key {attrs['attribute']} not found in template attribute. Adding anyway...")

			if args.append:
				temp_list = []
				if isinstance(target_template[0][attrs['attribute']].value, str):
					temp_list.append(target_template[0][attrs['attribute']].value)
				elif isinstance(target_template[0][attrs['attribute']].value, int):
					temp_list.append(target_template[0][attrs['attribute']].value)
				elif isinstance(target_template[0][attrs['attribute']].value, list):
					temp_list = target_template[0][attrs['attribute']].value
				attrs['value'] = list(set(attrs['value'] + temp_list))
			elif args.set:
				attrs['value'] = list(set(attrs['value']))

			attr_key = attrs['attribute']
			attr_val = attrs['value']

		try:
			succeeded = self.ldap_session.modify(target_template[0].entry_dn, {
				attr_key:[
					(ldap3.MODIFY_REPLACE,attr_val)
				]
			})
		except ldap3.core.exceptions.LDAPInvalidValueError as e:
			logging.error(f"[Set-DomainCATemplate] {str(e)}")
			succeeded = False

		if not succeeded:
			logging.error(self.ldap_session.result if self.args.debug else "[Set-DomainCATemplate] Failed to modify template")
		else:
			logging.info(f'[Set-DomainCATemplate] Success! modified attribute for {identity} template')

		return succeeded

	def add_domaingroupmember(self, identity, members, args=None):
		group_entry = self.get_domaingroup(identity=identity,properties=['distinguishedName'])
		user_entry = self.get_domainobject(identity=members,properties=['distinguishedName'])
		if len(group_entry) == 0:
			raise ValueError(f'[Add-DomainGroupMember] Group {identity} not found in domain')
		if len(user_entry) == 0:
			raise ValueError(f'[Add-DomainGroupMember] User {members} not found in domain. Try to use DN')
		targetobject = group_entry[0]
		userobject = user_entry[0]
		if isinstance(targetobject["attributes"]["distinguishedName"], list):
			targetobject_dn = targetobject["attributes"]["distinguishedName"][0]
		else:
			targetobject_dn = targetobject["attributes"]["distinguishedName"]

		if isinstance(userobject["attributes"]["distinguishedName"], list):
			userobject_dn = userobject["attributes"]["distinguishedName"][0]
		else:
			userobject_dn = userobject["attributes"]["distinguishedName"]
		
		try:
			succeeded = self.ldap_session.modify(targetobject_dn,{'member': [(ldap3.MODIFY_ADD, [userobject_dn])]})
		except ldap3.core.exceptions.LDAPInvalidValueError as e:
			logging.error(f"[Add-DomainGroupMember] {str(e)}")
			succeeded = False
		
		if not succeeded:
			raise ValueError(self.ldap_session.result['message'] if self.args.debug else f"[Add-DomainGroupMember] Failed to add {members} to group {identity}")
		return succeeded

	def disable_domaindnsrecord(self, recordname, zonename=None):
		succeed = self.set_domaindnsrecord(
			recordname=recordname,
			recordaddress="0.0.0.0",
			zonename=zonename,
		)

		if succeed:
			logging.info(f"[Disable-DomainDNSRecord] {recordname} dns record disabled")
			return True
		else:
			logging.error("[Disable-DomainDNSRecord] Failed to disable dns record")
			return False

	def remove_domaindnsrecord(self, recordname=None, zonename=None):
		if zonename:
			zonename = zonename.lower()
		else:
			zonename = self.domain.lower()
			logging.debug("[Remove-DomainDNSRecord] Using current domain %s as zone name" % zonename)

		zones = [name['attributes']['name'].lower() for name in self.get_domaindnszone(properties=['name'])]
		if zonename not in zones:
			logging.info("[Remove-DomainDNSRecord] Zone %s not found" % zonename)
			return

		entry = self.get_domaindnsrecord(identity=recordname, zonename=zonename)

		if len(entry) == 0:
			logging.info("[Remove-DomainDNSRecord] No record found")
			return
		elif len(entry) > 1:
			logging.error("[Remove-DomainDNSRecord] More than one record found")
			return

		record_dn = entry[0]["attributes"]["distinguishedName"]

		succeeded = self.ldap_session.delete(record_dn)
		if not succeeded:
			logging.error(self.ldap_session.result['message'] if self.args.debug else "[Remove-DomainDNSRecord] Failed to delete record")
			return False
		else:
			logging.info("[Remove-DomainDNSRecord] Success! Deleted the record")
			return True

	def remove_domaingroupmember(self, identity, members, args=None):
		group_entry = self.get_domaingroup(identity=identity,properties=['distinguishedName'])
		user_entry = self.get_domainobject(identity=members,properties=['distinguishedName'])
		if len(group_entry) == 0:
			logging.error(f'[Remove-DomainGroupmember] Group {identity} not found in domain')
			return
		if len(user_entry) == 0:
			logging.error(f'[Remove-DomainGroupMember] User {members} not found in domain, Try to use DN')
			return
		targetobject = group_entry[0]
		userobject = user_entry[0]
		if isinstance(targetobject["attributes"]["distinguishedName"], list):
			targetobject_dn = targetobject["attributes"]["distinguishedName"][0]
		else:
			targetobject_dn = targetobject["attributes"]["distinguishedName"]

		if isinstance(userobject["attributes"]["distinguishedName"], list):
			userobject_dn = userobject["attributes"]["distinguishedName"][0]
		else:
			userobject_dn = userobject["attributes"]["distinguishedName"]
		succeeded = self.ldap_session.modify(targetobject_dn,{'member': [(ldap3.MODIFY_DELETE, [userobject_dn])]})
		if not succeeded:
			print(self.ldap_session.result['message'])
		return succeeded

	def remove_domainuser(self, identity):
		if not identity:
			logging.error('[Remove-DomainUser] Identity is required')
			return
		entries = self.get_domainuser(identity=identity)
		if len(entries) == 0:
			logging.error('[Remove-DomainUser] Identity not found in domain')
			return
		identity_dn = entries[0]["attributes"]["distinguishedName"]
		au = ADUser(self.ldap_session, self.root_dn)
		return au.removeUser(identity_dn)

	def add_domaingroup(self, groupname, basedn=None, args=None):
		parent_dn_entries = f"CN=Users,{self.root_dn}"
		if basedn:
			parent_dn_entries = basedn
		if hasattr(args, 'basedn') and args.basedn:
			parent_dn_entries = args.basedn

		entries = self.get_domainobject(identity=parent_dn_entries)
		if len(entries) <= 0:
			logging.error(f"[Add-DomainGroup] {parent_dn_entries} could not be found in the domain")
			return
		elif len(entries) > 1:
			logging.error("[Add-DomainGroup] More than one group found in domain")
			return

		parent_dn_entries = entries[0]["attributes"]["distinguishedName"]
		logging.debug(f"[Add-DomainGroup] Adding group in {parent_dn_entries}")

		group_dn = f"CN={groupname},{parent_dn_entries}"
		ucd = {
			'displayName': groupname,
			'sAMAccountName': groupname,
			'objectCategory': 'CN=Group,CN=Schema,CN=Configuration,%s' % self.root_dn,
			'objectClass': ['top', 'group'],
		}

		succeed = self.ldap_session.add(group_dn, ['top', 'group'], ucd)
		if not succeed:
			logging.error(f"[Add-DomainGroup] Failed adding {groupname} to domain ({self.ldap_session.result['description']})")
			return False
		else:
			logging.info('[Add-DomainGroup] Success! Created new group')
			return True

	def add_domainuser(self, username, userpass, basedn=None, args=None):
		parent_dn_entries = f"CN=Users,{self.root_dn}"
		if basedn:
			parent_dn_entries = basedn
		if hasattr(args, 'basedn') and args.basedn:
			parent_dn_entries = args.basedn

		entries = self.get_domainobject(identity=parent_dn_entries)
		if len(entries) <= 0:
			logging.error(f"[Add-DomainUser] {parent_dn_entries} could not be found in the domain")
			return
		elif len(entries) > 1:
			logging.error("[Add-DomainUser] More than one group found in domain")
			return

		parent_dn_entries = entries[0]["attributes"]["distinguishedName"]

		logging.debug(f"[Add-DomainUser] Adding user in {parent_dn_entries}")
		
		if self.use_ldaps:
			logging.warning("[Add-DomainUser] Adding user through LDAPS")
			au = ADUser(self.ldap_session, self.root_dn, parent = parent_dn_entries)
			succeed = au.addUser(username, userpass)
		else:
			logging.warning("[Add-DomainUser] Adding user through LDAP")
			udn = "CN=%s,%s" % (
						username,
						parent_dn_entries
					)
			ucd = {
				'displayName': username,
				'sAMAccountName': username,
				'userPrincipalName': f"{username}@{self.root_dn}",
				'name': username,
				'givenName': username,
				'sn': username,
				'userAccountControl': ['66080'],
			}
			succeed = self.ldap_session.add(udn, ['top', 'person', 'organizationalPerson', 'user'], ucd)
			
		if not succeed:
			logging.error(self.ldap_session.result['message'] if self.args.debug else f"[Add-DomainUser] Failed adding {username} to domain ({self.ldap_session.result['description']})")
			return False
		else:
			logging.info('[Add-DomainUser] Success! Created new user')

			if not self.use_ldaps:
				logging.info("[Add-DomainUser] Adding password to account")
				self.set_domainuserpassword(udn, userpass)
			
			return True

	def remove_domainobjectacl(self, targetidentity, principalidentity, rights="fullcontrol", rights_guid=None, ace_type="allowed", inheritance=False):
		# verify if target identity exists
		target_entries = self.get_domainobject(identity=targetidentity, properties=['objectSid', 'distinguishedName', 'sAMAccountName','nTSecurityDescriptor'], sd_flag=0x04)
		
		target_dn = None
		target_sAMAccountName = None
		target_SID = None
		target_security_descriptor = None
		
		if len(target_entries) == 0:
			logging.error('[Remove-DomainObjectACL] Target Identity object not found in domain')
			return
		elif len(target_entries) > 1:
			logging.error("[Remove-DomainObjectACL] More then one target identity found")
			return

		target_dn = target_entries[0].get("dn") #target_DN
		target_sAMAccountName = target_entries[0].get("attributes").get("sAMAccountName") #target_sAMAccountName
		target_SID = target_entries[0].get("attributes").get("objectSid") #target_SID
		target_security_descriptor = target_entries[0].get("raw_attributes").get("nTSecurityDescriptor")[0]

		logging.info(f'[Remove-DomainObjectACL] Found target identity: {target_dn if target_dn else target_sAMAccountName}')
		
		# verify if principalidentity exists
		principal_entries = self.get_domainobject(identity=principalidentity, properties=['objectSid', 'distinguishedName', 'sAMAccountName'])
		
		principal_dn = None
		principal_sAMAccountName = None
		principal_SID = None

		if len(principal_entries) == 0:
			logging.debug('[Remove-DomainObjectAcl] Principal not found. Searching in Well Known SIDs...')
			well_known_obj = resolve_WellKnownSID(principalidentity)
			principal_sAMAccountName = well_known_obj.get("sAMAccountName")
			principal_SID = well_known_obj.get("objectSid")
			if principal_SID:
				logging.debug("[Remove-DomainObjectAcl] Found in well known SID: %s" % principal_SID)
			else:
				logging.error('[Remove-DomainObjectACL] Principal Identity object not found in domain')
				return
		elif len(principal_entries) > 1:
			logging.error("[Remove-DomainObjectACL] More then one principal identity found")
			return

		principal_dn = principal_entries[0].get("dn") if principal_entries else principal_dn #principal_DN
		principal_sAMAccountName = principal_entries[0].get("attributes").get("sAMAccountName") if principal_entries else principal_sAMAccountName #principal_sAMAccountName
		principal_SID = principal_entries[0].get("attributes").get("objectSid") if principal_entries else principal_SID #principal_SID

		logging.info(f'[Remove-DomainObjectACL] Found principal identity: {principal_dn if principal_dn else principal_sAMAccountName}')
		
		dacledit = DACLedit(
				self.ldap_server,
				self.ldap_session,
				self.root_dn,
				target_sAMAccountName,
				target_SID,
				target_dn,
				target_security_descriptor,
				principal_sAMAccountName,
				principal_SID,
				principal_dn,
				ace_type,
				rights,
				rights_guid,
				inheritance
			)
		dacledit.remove()

	def add_domainobjectacl(self, targetidentity, principalidentity, rights="fullcontrol", rights_guid=None, ace_type="allowed", inheritance=False):
		# verify if target identity exists
		target_entries = self.get_domainobject(identity=targetidentity, properties=['objectSid', 'distinguishedName', 'sAMAccountName','nTSecurityDescriptor'], sd_flag=0x04)
		
		target_dn = None
		target_sAMAccountName = None
		target_SID = None
		
		if len(target_entries) == 0:
			logging.error('[Add-DomainObjectACL] Target Identity object not found in domain')
			return
		elif len(target_entries) > 1:
			logging.error("[Add-DomainObjectACL] More then one target identity found")
			return

		target_dn = target_entries[0].get("dn") #target_DN
		target_sAMAccountName = target_entries[0].get("attributes").get("sAMAccountName") #target_sAMAccountName
		target_SID = target_entries[0].get("attributes").get("objectSid") #target_SID
		target_security_descriptor = target_entries[0].get("raw_attributes").get("nTSecurityDescriptor")[0]

		logging.info(f'[Add-DomainObjectACL] Found target identity: {target_dn if target_dn else target_sAMAccountName}')
		
		# verify if principalidentity exists
		principal_entries = self.get_domainobject(identity=principalidentity, properties=['objectSid', 'distinguishedName', 'sAMAccountName'])
		
		principal_dn = None
		principal_sAMAccountName = None
		principal_SID = None

		if len(principal_entries) == 0:
			logging.debug('[Add-DomainObjectAcl] Principal not found. Searching in Well Known SIDs...')
			well_known_obj = resolve_WellKnownSID(principalidentity)
			principal_sAMAccountName = well_known_obj.get("sAMAccountName")
			principal_SID = well_known_obj.get("objectSid")
			if principal_SID:
				logging.debug("[Add-DomainObjectAcl] Found in well known SID: %s" % principal_SID)
			else:
				logging.error('[Add-DomainObjectACL] Principal Identity object not found in domain')
				return
		elif len(principal_entries) > 1:
			logging.error("[Add-DomainObjectACL] More then one principal identity found")
			return

		principal_dn = principal_entries[0].get("dn") if principal_entries else principal_dn #principal_DN
		principal_sAMAccountName = principal_entries[0].get("attributes").get("sAMAccountName") if principal_entries else principal_sAMAccountName #principal_sAMAccountName
		principal_SID = principal_entries[0].get("attributes").get("objectSid") if principal_entries else principal_SID #principal_SID

		logging.info(f'[Add-DomainObjectACL] Found principal identity: {principal_dn if principal_dn else principal_sAMAccountName}')
		
		dacledit = DACLedit(
				self.ldap_server,
				self.ldap_session,
				self.root_dn,
				target_sAMAccountName,
				target_SID,
				target_dn,
				target_security_descriptor,
				principal_sAMAccountName,
				principal_SID,
				principal_dn,
				ace_type,
				rights,
				rights_guid,
				inheritance
			)
		dacledit.write()

	def remove_domaincomputer(self, computer_name, args=None):
		parent_dn_entries = self.root_dn
		if hasattr(args, 'basedn') and args.basedn:
			entries = self.get_domainobject(identity=args.basedn)
			if len(entries) <= 0:
				logging.error(f"[Add-DomainComputer] {args.basedn} could not be found in the domain")
				return
			elif len(entries) > 1:
				logging.error("[Add-DomainComputer] More then one computer found in domain")
				return

			parent_dn_entries = entries[0]["attributes"]["distinguishedName"]
		
		setattr(self.args, "TGT", self.conn.get_TGT())
		setattr(self.args, "TGS", self.conn.get_TGS())
		setattr(self.args, "dc_host", self.dc_dnshostname)
		setattr(self.args, "delete", True)

		if self.use_ldaps:
			setattr(self.args, "method", "LDAPS")
		else:
			setattr(self.args, "method", "SAMR")

		# Creating Machine Account
		addmachineaccount = ADDCOMPUTER(
				username = self.username,
				password = self.password,
				domain = self.domain,
				cmdLineOptions = self.args,
				computer_name = computer_name,
				base_dn = parent_dn_entries,
				ldap_session = self.ldap_session
				)
		try:
			if self.use_ldaps:
				addmachineaccount.run_ldaps()
			else:
				addmachineaccount.run_samr()
		except Exception as e:
			logging.error(str(e))
			return False

		if len(self.get_domainobject(identity=computer_name)) == 0:
			return True
		else:
			return False

	def set_domaindnsrecord(self, recordname, recordaddress, zonename=None):
		if zonename:
			zonename = zonename.lower()
		else:
			zonename = self.domain.lower()
			logging.debug("[Set-DomainDNSRecord] Using current domain %s as zone name" % zonename)

		entry = self.get_domaindnsrecord(identity=recordname, zonename=zonename, properties=['dnsRecord', 'distinguishedName', 'name'])

		if not entry:
			return
		elif len(entry) == 0:
			logging.info("[Set-DomainDNSRecord] No record found")
			return
		elif len(entry) > 1:
			logging.info("[Set-DomainDNSRecord] More than one record found")
			return

		if self.args.debug:
			logging.debug(f"[Set-DomainDNSRecord] Updating dns record {recordname} to {recordaddress}")

		targetrecord = None
		records = []
		for record in entry[0]["attributes"]["dnsRecord"]:
			dr = DNS_RECORD(record)
			if dr["Type"] == 1:
				targetrecord = dr
			else:
				records.append(record)

		if not targetrecord:
			logging.error("[Set-DomainDNSRecord] No A record exists yet. Nothing to modify")
			return

		targetrecord["Serial"] = DNS_UTIL.get_next_serial(self.dc_ip, zonename, True)
		targetrecord['Data'] = DNS_RPC_RECORD_A()
		targetrecord['Data'].fromCanonical(recordaddress)
		records.append(targetrecord.getData())

		succeeded = self.ldap_session.modify(entry[0]['attributes']['distinguishedName'], {'dnsRecord': [(ldap3.MODIFY_REPLACE, records)]})

		if not succeeded:
			logging.error(self.ldap_session.result['message'])
			return False
		else:
			logging.info('[Set-DomainDNSRecord] Success! modified attribute for target record %s' % entry[0]['attributes']['distinguishedName'])
			return True

	def add_domaindnsrecord(self, recordname, recordaddress, zonename=None):
		if zonename:
			zonename = zonename.lower()
		else:
			zonename = self.domain.lower()
			logging.debug("[Add-DomainDNSRecord] Using current domain %s as zone name" % zonename)

		zones = [name['attributes']['name'].lower() for name in self.get_domaindnszone(properties=['name'])]
		if zonename not in zones:
			logging.info("[Add-DomainDNSRecord] Zone %s not found" % zonename)
			return

		if recordname.lower().endswith(zonename.lower()):
			recordname = recordname[:-(len(zonename)+1)]

		# addtype is A record = 1
		addtype = 1
		DNS_UTIL.get_next_serial(self.dc_ip, zonename, True)
		node_data = {
				# Schema is in the root domain (take if from schemaNamingContext to be sure)
				'objectCategory': 'CN=Dns-Node,CN=Schema,CN=Configuration,%s' % self.root_dn,
				'dNSTombstoned': "FALSE", # Need to hardcoded because of Kerberos issue, will revisit.
				'name': recordname
				}
		logging.debug("[Add-DomainDNSRecord] Creating DNS record structure")
		record = DNS_UTIL.new_record(addtype, DNS_UTIL.get_next_serial(self.dc_ip, zonename, True), recordaddress)
		search_base = f"DC={zonename},CN=MicrosoftDNS,DC=DomainDnsZones,{self.root_dn}"
		record_dn = 'DC=%s,%s' % (recordname, search_base)
		node_data['dnsRecord'] = [record.getData()]
		
		succeeded = self.ldap_session.add(record_dn, ['top', 'dnsNode'], node_data)
		if not succeeded:
			logging.error(self.ldap_session.result['message'] if self.args.debug else f"[Add-DomainDNSRecord] Failed adding DNS record to domain ({self.ldap_session.result['description']})")
			return False
		else:
			logging.info('[Add-DomainDNSRecord] Success! Created new record with dn %s' % record_dn)
			return True

	def add_domaincomputer(self, computer_name, computer_pass, basedn=None, args=None):
		parent_dn_entries = f"CN=Computers,{self.root_dn}"
		if basedn:
			parent_dn_entries = basedn
		if hasattr(args, 'basedn') and args.basedn:
			entries = self.get_domainobject(identity=args.basedn)
			if len(entries) <= 0:
				logging.error(f"[Add-DomainComputer] {args.basedn} could not be found in the domain")
				return
			elif len(entries) > 1:
				logging.error("[Add-DomainComputer] More then one computer found in domain")
				return

			parent_dn_entries = entries[0]["attributes"]["distinguishedName"]
		
		if computer_name[-1] != '$':
			computer_name += '$'

		setattr(self.args, "TGT", self.conn.get_TGT())
		setattr(self.args, "TGS", self.conn.get_TGS())
		setattr(self.args, "dc_host", self.dc_dnshostname)
		setattr(self.args, "delete", False)

		if self.use_ldaps:
			setattr(self.args, "method", "LDAPS")
		else:
			setattr(self.args, "method", "SAMR")

		# Creating Machine Account
		addmachineaccount = ADDCOMPUTER(
				username=self.username,
				password=self.password,
				domain=self.domain,
				cmdLineOptions = self.args,
				computer_name = computer_name,
				computer_pass = computer_pass,
				base_dn = parent_dn_entries,
				ldap_session = self.ldap_session
		)
		try:
			if self.use_ldaps:
				logging.debug("[Add-DomainComputer] Adding computer via LDAPS")
				addmachineaccount.run_ldaps()
			else:
				logging.debug("[Add-DomainComputer] Adding computer via SAMR")
				addmachineaccount.run_samr()
		except Exception as e:
			logging.error(str(e))
			return False

		if self.get_domainobject(identity=computer_name)[0]['attributes']['distinguishedName']:
			return True
		else:
			return False

	def get_namedpipes(self, args=None):
		host = ""
		is_fqdn = False
		host_inp = args.computer if args.computer else args.computername

		if host_inp:
			if not is_ipaddress(host_inp):
				is_fqdn = True
				if args.server and args.server.casefold() != self.domain.casefold():
					if not host_inp.endswith(args.server):
						host = f"{host_inp}.{args.server}"
					else:
						host = host_inp
				else:
					if not is_valid_fqdn(host_inp):
						host = f"{host_inp}.{self.domain}"
					else:
						host = host_inp
				logging.debug(f"[Get-NamedPipes] Using FQDN: {host}")
			else:
				host = host_inp

		if self.use_kerberos:
			if is_ipaddress(args.computer) or is_ipaddress(args.computername):
				logging.error('[Get-NamedPipes] FQDN must be used for kerberos authentication')
				return
		else:
			if is_fqdn:
				host = host2ip(host, self.nameserver, 3, True, use_system_ns=self.use_system_nameserver)

		if not host:
			logging.error('[Get-NamedPipes] Host not found')
			return

		result = {
				"headers":["Name", "Protocol", "Description", "Authenticated"],
				"rows":[]
				}
		entries = []
		entry = {
			"Name": None,
			"Protocol": None,
			"Description": None,
			"Authenticated": None
		}
		binding_params = {
				'lsarpc': {
					'stringBinding': r'ncacn_np:%s[\PIPE\lsarpc]' % host,
					'protocol': 'MS-EFSRPC',
					'description': 'Encrypting File System Remote (EFSRPC) Protocol',
					},
				'efsr': {
					'stringBinding': r'ncacn_np:%s[\PIPE\efsrpc]' % host,
					'protocol': 'MS-EFSR',
					'description': 'Encrypting File System Remote (EFSRPC) Protocol',
					},
				'samr': {
					'stringBinding': r'ncacn_np:%s[\PIPE\samr]' % host,
					'protocol': 'MS-SAMR',
					'description': 'Security Account Manager (SAM) Remote Protocol',
					},
				'lsass': {
					'stringBinding': r'ncacn_np:%s[\PIPE\lsass]' % host,
					'protocol': 'N/A',
					'description': 'N/A',
					},
				'netlogon': {
					'stringBinding': r'ncacn_np:%s[\PIPE\netlogon]' % host,
					'protocol': 'MS-NRPC',
					'description': 'Netlogon Remote Protocol',
					},
				'spoolss': {
					'stringBinding': r'ncacn_np:%s[\PIPE\spoolss]' % host,
					'protocol': 'MS-RPRN',
					'description': 'Print System Remote Protocol',
					},
				'DAV RPC SERVICE': {
					'stringBinding': r'ncacn_np:%s[\PIPE\DAV RPC SERVICE]' % host,
					'protocol': 'WebClient',
					'description': 'WebDAV WebClient Service',
					},
				'netdfs': {
					'stringBinding': r'ncacn_np:%s[\PIPE\netdfs]' % host,
					'protocol': 'MS-DFSNM',
					'description': 'Distributed File System (DFS)',
					},
				'atsvc': {
					'stringBinding': r'ncacn_np:%s[\PIPE\atsvc]' % host,
					'protocol': 'ATSvc',
					'description': 'Microsoft AT-Scheduler Service',
					},
				}

		if args.name:
			if args.name in list(binding_params.keys()):
				pipe = args.name
				entry["Name"] = pipe
				entry["Protocol"] = binding_params[pipe]['protocol']
				entry["Description"] = binding_params[pipe]['description']
				if self.conn.connectRPCTransport(host, binding_params[pipe]['stringBinding'], auth=False, set_authn=True):
					#result["rows"].append([pipe, binding_params[pipe]['protocol'], binding_params[pipe]['description'], f'{bcolors.WARNING}No{bcolors.ENDC}'])
					entry ["Authenticated"] = f'{bcolors.WARNING}No{bcolors.ENDC}'
				elif self.conn.connectRPCTransport(host, binding_params[pipe]['stringBinding'], set_authn=True):
					#result["rows"].append([pipe, binding_params[pipe]['protocol'], binding_params[pipe]['description'], f'{bcolors.OKGREEN}Yes{bcolors.ENDC}'])
					entry ["Authenticated"] = f'{bcolors.OKGREEN}Yes{bcolors.ENDC}'
				entries.append(
					{
						"attributes": dict(entry)
					}
				)
			else:
				logging.error("[Get-NamedPipes] Pipe not found")
				return
		else:
			for pipe in binding_params.keys():
				# TODO: Return entries
				entry["Name"] = pipe
				entry["Protocol"] = binding_params[pipe]['protocol']
				entry["Description"] = binding_params[pipe]['description']
				if self.conn.connectRPCTransport(host, binding_params[pipe]['stringBinding'], auth=False, set_authn=True):
					#logging.debug(f"Found named pipe: {pipe}")
					#result["rows"].append([pipe, binding_params[pipe]['protocol'], binding_params[pipe]['description'], f'{bcolors.WARNING}No{bcolors.ENDC}'])
					entry ["Authenticated"] = f'{bcolors.WARNING}No{bcolors.ENDC}'
				elif self.conn.connectRPCTransport(host, binding_params[pipe]['stringBinding'], set_authn=True):
					#result["rows"].append([pipe, binding_params[pipe]['protocol'], binding_params[pipe]['description'], f'{bcolors.OKGREEN}Yes{bcolors.ENDC}'])
					entry ["Authenticated"] = f'{bcolors.OKGREEN}Yes{bcolors.ENDC}'
				entries.append(
					{
						"attributes": dict(entry)
					}
				)

		return entries

	def set_domainuserpassword(self, identity, accountpassword, oldpassword=None, args=None):
		entries = self.get_domainuser(identity=identity, properties=['distinguishedName','sAMAccountName'])
		if len(entries) == 0:
			logging.error(f'[Set-DomainUserPassword] No principal object found in domain')
			return
		elif len(entries) > 1:
			logging.error(f'[Set-DomainUserPassword] Multiple principal objects found in domain. Use specific identifier')
			return
		logging.info(f'[Set-DomainUserPassword] Principal {"".join(entries[0]["attributes"]["distinguishedName"])} found in domain')
		if self.use_ldaps:
			logging.debug("[Set-DomainUserPassword] Using LDAPS to change %s password" % (entries[0]["attributes"]["sAMAccountName"]))
			succeed = modifyPassword.ad_modify_password(self.ldap_session, entries[0]["attributes"]["distinguishedName"], accountpassword, old_password=oldpassword)
			if succeed:
				logging.info(f'[Set-DomainUserPassword] Password has been successfully changed for user {"".join(entries[0]["attributes"]["sAMAccountName"])}')
				return True
			else:
				logging.error(f'[Set-DomainUserPassword] Failed to change password for {"".join(entries[0]["attributes"]["sAMAccountName"])}')
				return False
		else:
			logging.debug("[Set-DomainUserPassword] Using SAMR to change %s password" % (entries[0]["attributes"]["sAMAccountName"]))
			try:
				dce = self.conn.init_samr_session()
				if not dce:
					logging.error('Error binding with SAMR')
					return

				server_handle = samr.hSamrConnect(dce, self.dc_ip + '\x00')['ServerHandle']
				domainSID = samr.hSamrLookupDomainInSamServer(dce, server_handle, self.domain)['DomainId']
				domain_handle = samr.hSamrOpenDomain(dce, server_handle, domainId=domainSID)['DomainHandle']
				userRID = samr.hSamrLookupNamesInDomain(dce, domain_handle, (entries[0]['attributes']['sAMAccountName'],))['RelativeIds']['Element'][0]
				opened_user = samr.hSamrOpenUser(dce, domain_handle, userId=userRID)

				req = samr.SamrSetInformationUser2()
				req['UserHandle'] = opened_user['UserHandle']
				req['UserInformationClass'] = samr.USER_INFORMATION_CLASS.UserInternal5Information
				req['Buffer'] = samr.SAMPR_USER_INFO_BUFFER()
				req['Buffer']['tag'] = samr.USER_INFORMATION_CLASS.UserInternal5Information
				req['Buffer']['Internal5']['UserPassword'] = cryptPassword(b'SystemLibraryDTC', accountpassword)
				req['Buffer']['Internal5']['PasswordExpired'] = 0

				resp = dce.request(req)
				logging.info(f'[Set-DomainUserPassword] Password has been successfully changed for user {"".join(entries[0]["attributes"]["sAMAccountName"])}')
				return True
			except:
				logging.error(f'[Set-DomainUserPassword] Failed to change password for {"".join(entries[0]["attributes"]["sAMAccountName"])}')
				return False

	def set_domaincomputerpassword(self, identity, accountpassword, oldpassword=None, args=None):
		entries = self.get_domaincomputer(identity=identity, properties=[
			'distinguishedName',
			'sAMAccountName',
			])
		if len(entries) == 0:
			logging.error("[Get-DomainComputerPassword] Computer %s not found in domain" % (identity))
			return False
		elif len(entries) > 1:
			logging.error("[Get-DomainComputerPassword] Multiple computers found in domain")
			return False

		if self.use_ldaps:
			logging.debug("[Set-DomainComputerPassword] Using LDAPS to change %s password" % (entries[0]["attributes"]["sAMAccountName"]))
			succeed = modifyPassword.ad_modify_password(self.ldap_session, entries[0]["attributes"]["distinguishedName"], accountpassword, old_password=oldpassword)
			if succeed:
				logging.info(f'[Set-DomainComputerPassword] Password has been successfully changed for user {entries[0]["attributes"]["sAMAccountName"]}')
				return True
			else:
				logging.error(f'[Set-DomainComputerPassword] Failed to change password for {entries[0]["attributes"]["sAMAccountName"]}')
				return False
		else:
			logging.debug("[Set-DomainComputerPassword] Using SAMR to change %s password" % (entries[0]["attributes"]["sAMAccountName"]))
			try:
				dce = self.conn.init_samr_session()
				if not dce:
					logging.error('Error binding with SAMR')
					return

				server_handle = samr.hSamrConnect(dce, self.dc_ip + '\x00')['ServerHandle']
				domainSID = samr.hSamrLookupDomainInSamServer(dce, server_handle, self.domain)['DomainId']
				domain_handle = samr.hSamrOpenDomain(dce, server_handle, domainId=domainSID)['DomainHandle']
				userRID = samr.hSamrLookupNamesInDomain(dce, domain_handle, (entries[0]['attributes']['sAMAccountName'],))['RelativeIds']['Element'][0]
				opened_user = samr.hSamrOpenUser(dce, domain_handle, userId=userRID)

				req = samr.SamrSetInformationUser2()
				req['UserHandle'] = opened_user['UserHandle']
				req['UserInformationClass'] = samr.USER_INFORMATION_CLASS.UserInternal5Information
				req['Buffer'] = samr.SAMPR_USER_INFO_BUFFER()
				req['Buffer']['tag'] = samr.USER_INFORMATION_CLASS.UserInternal5Information
				req['Buffer']['Internal5']['UserPassword'] = cryptPassword(b'SystemLibraryDTC', accountpassword)
				req['Buffer']['Internal5']['PasswordExpired'] = 0

				resp = dce.request(req)
				logging.info(f'[Set-DomainComputerPassword] Password has been successfully changed for user {"".join(entries[0]["attributes"]["sAMAccountName"])}')
				return True
			except:
				logging.error(f'[Set-DomainComputerPassword] Failed to change password for {"".join(entries[0]["attributes"]["sAMAccountName"])}')
				return False


	def set_domainobject(self, identity, clear=None, _set=None, append=None, searchbase=None, sd_flag=None, args=None):
		if _set and clear and append:
			raise ValueError("Cannot use 'clear', 'set', and 'append' options simultaneously. Choose one operation.")

		if not searchbase:
			searchbase = args.searchbase if hasattr(args, 'searchbase') and args.searchbase else self.root_dn

		targetobject = self.get_domainobject(identity=identity, searchbase=searchbase, properties=['*'], sd_flag=sd_flag)
		if len(targetobject) > 1:
			logging.error(f"[Set-DomainObject] More than one identity found. Use distinguishedName instead")
			return False
		elif len(targetobject) == 0:
			logging.error(f"[Set-DomainObject] Identity {identity} not found in domain")
			return False

		attr_clear = args.clear if hasattr(args,'clear') and args.clear else clear
		attr_set = args.set if hasattr(args, 'set') and args.set else _set
		attr_append = args.append if hasattr(args, 'append') and args.append else append

		attr_key = ""
		attr_val = []

		if attr_clear:
			attr_key = attr_clear
		else:
			attrs = {}

			if attr_set:
				if isinstance(attr_set, dict):
					attrs = attr_set
				else:
					attrs = ini_to_dict(attr_set)
			elif attr_append:
				if isinstance(attr_append, dict):
					attrs = attr_append
				else:
					attrs = ini_to_dict(attr_append)
			if not attrs:
				raise ValueError(f"[Set-DomainObject] Parsing {'-Set' if args.set else '-Append'} value failed")

			# check if value is a file
			if len(attrs['value']) == 1 and isinstance(attrs['value'][0], str) and not isinstance(attrs['value'][0], bytes) and attrs['value'][0].startswith("@"):
				path = attrs['value'][0].lstrip("@")
				try:
					logging.debug("[Set-DomainObject] Reading from file")
					attrs['value'][0] = read_file(path, mode ="rb")
				except Exception as e:
					logging.error("[Set-DomainObject] %s" % str(e))
					return

			try:
				if isinstance(attrs['value'], list):
					for val in attrs['value']:
						try:
							values = targetobject[0]["attributes"].get(attrs['attribute'])
							if isinstance(values, list):
								for ori_val in values:
									if isinstance(ori_val, str) and isinstance(val, str):
										if val.casefold() == ori_val.casefold():
											raise ValueError(f"[Set-DomainObject] Value {val} already set in the attribute "+attrs['attribute'])
									else:
										if val == values:
											raise ValueError(f"[Set-DomainObject] Value {val} already set in the attribute "+attrs['attribute'])
							elif isinstance(values, str):
								if val.casefold() == values.casefold():
									raise ValueError(f"[Set-DomainObject] Value {val} already set in the attribute "+attrs['attribute'])
							else:
								if val == values:
									raise ValueError(f"[Set-DomainObject] Value {val} already set in the attribute "+attrs['attribute'])
						except KeyError as e:
							logging.warning(f"[Set-DomainObject] Attribute {attrs['attribute']} not exists in object. Modifying anyway...")
			except ldap3.core.exceptions.LDAPKeyError as e:
				logging.error(f"[Set-DomainObject] Key {attrs['attribute']} not found in template attribute. Adding anyway...")

			if attr_append:
				if not targetobject[0]["attributes"].get(attrs['attribute']):
					logging.warning(f"[Set-DomainObject] {attrs['attribute']} property not found in target identity")
					logging.warning(f"[Set-DomainObject] Attempting to force add attribute {attrs['attribute']} to target object")
					return self.set_domainobject(identity, _set={
						'attribute': attrs['attribute'],
						'value': attrs['value'],
						},
												 searchbase=searchbase,
												 sd_flag=sd_flag
												 )

				temp_list = []
				if isinstance(targetobject[0]["attributes"][attrs['attribute']], str):
					if len(targetobject[0]["attributes"][attrs['attribute']].strip()) != 0:
						temp_list.append(targetobject[0]["attributes"][attrs['attribute']])
				elif isinstance(targetobject[0]["attributes"][attrs['attribute']], int):
					temp_list.append(targetobject[0]["attributes"][attrs['attribute']])
				elif isinstance(targetobject[0]["attributes"][attrs['attribute']], list):
					temp_list = targetobject[0]["attributes"][attrs['attribute']]

				#In case the value a Distinguished Name we retransform it into a list to append it
				if re.search(r'^((CN=([^,]*)),)?((((?:CN|OU)=[^,]+,?)+),)?((DC=[^,]+,?)+)$', str(attrs['value'])):
					attrs['value'] = list(set(list(attrs['value'].split('\n') + temp_list)))
				else:
					attrs['value'] = list(set(attrs['value'] + temp_list))
			elif attr_set:
				#In case the value is a Distinguished Name
				if not re.search(r'^((CN=([^,]*)),)?((((?:CN|OU)=[^,]+,?)+),)?((DC=[^,]+,?)+)$', str(attrs['value'])):
					attrs['value'] = list(set(attrs['value']))

			attr_key = attrs['attribute']
			attr_val = attrs['value']

		try:
			succeeded = self.ldap_session.modify(targetobject[0]["attributes"]["distinguishedName"], {
				attr_key:[
					(ldap3.MODIFY_REPLACE,attr_val)
					]
				}, controls=security_descriptor_control(sdflags=sd_flag) if sd_flag else None)
		except ldap3.core.exceptions.LDAPInsufficientAccessRightsResult as e:
			raise ValueError(f"[Set-DomainObject] Insufficient access rights to modify {attr_key}: {str(e)}")
		except ldap3.core.exceptions.LDAPInvalidValueError as e:
			raise ValueError(f"[Set-DomainObject] Invalid value for {attr_key}: {str(e)}")

		if not succeeded:
			logging.error(f"[Set-DomainObject] Failed to modify attribute {attr_key} for {targetobject[0]['attributes']['distinguishedName']}")
			logging.error(self.ldap_session.result['message'] )
		else:
			logging.info(f'[Set-DomainObject] Success! modified attribute {attr_key} for {targetobject[0]["attributes"]["distinguishedName"]}')

		return succeeded

	def set_domainobjectdn(self, identity, destination_dn, searchbase=None, sd_flag=None, args=None):
		if not searchbase:
			searchbase = args.searchbase if hasattr(args, 'searchbase') and args.searchbase else self.root_dn

		# verify if the identity exists
		targetobject = self.get_domainobject(identity=identity, searchbase=searchbase, properties=['*'], sd_flag=sd_flag)
		if len(targetobject) > 1:
			logging.error(f"[Set-DomainObjectDN] More than one {identity} object found in domain. Try using distinguishedName instead")
			return False
		elif len(targetobject) == 0:
			logging.error(f"[Set-DomainObjectDN] {identity} not found in domain")
			return False

		# verify if the destination_dn exists
		new_dn = self.get_domainobject(identity=destination_dn, searchbase=searchbase, properties=['*'])
		if not new_dn:
			logging.error(f"[Set-DomainObjectDN] Object {destination_dn} not found in domain")
			return False
		
		# set the object new dn
		if isinstance(targetobject, list):
			targetobject_dn = targetobject[0]["attributes"]["distinguishedName"]
		else:
			targetobject_dn = targetobject["attributes"]["distinguishedName"]

		logging.debug(f"[Set-DomainObjectDN] Modifying {targetobject_dn} object dn to {destination_dn}")

		relative_dn = targetobject_dn.split(",")[0]

		succeeded = self.ldap_session.modify_dn(targetobject_dn, relative_dn, new_superior=destination_dn)
		if not succeeded:
			logging.error(self.ldap_session.result['message'] if self.args.debug else f"[Set-DomainObjectDN] Failed to modify, view debug message with --debug")
		else:
			logging.info(f'[Set-DomainObject] Success! modified new dn for {targetobject_dn}')

		return succeeded

	def invoke_kerberoast(self, args, properties=[]):
		# look for users with SPN set
		setattr(args, 'spn', True)
		entries = self.get_domainuser(args)
		if len(entries) == 0:
			logging.debug("[Invoke-Kerberoast] No identity found")
			return

		# request TGS for each accounts
		target_domain = self.domain

		if args.server:
			target_domain = args.server

		kdc_options = None
		enctype = None
		if args.opsec:
			enctype = 18 # aes
			kdc_options = "0x40810000"

		userspn = GetUserSPNs(self.username, self.password, self.domain, target_domain, self.args, identity=args.identity, options=kdc_options, encType=enctype, TGT=self.conn.get_TGT())
		entries_out = userspn.run(entries)

		# properly formatted for output
		entries.clear()
		entries = []
		if properties:
			for ent in entries_out:
				entries.append({
					'attributes': filter_entry(ent['attributes'],properties)
					})
		else:
			entries = entries_out

		return entries

	def find_localadminaccess(self, args):
		host_entries = []
		hosts = {}

		computer = args.computer if args.computer else args.computername

		if not is_valid_fqdn(computer) and self.use_kerberos:
			logging.error('[Find-LocaAdminAccess] FQDN must be used for kerberos authentication')
			return

		if computer:
			if not is_valid_fqdn(computer):
				computer = "%s.%s" % (computer,self.domain)

			if is_ipaddress(computer):
				hosts['address'] = computer
			else:
				hosts['address'] = host2ip(computer, self.nameserver, 3, True, use_system_ns=self.use_system_nameserver)
				hosts['hostname'] = computer
			host_entries.append(hosts)
		else:
			entries = self.get_domaincomputer(properties=['dnsHostName'])

			logging.info(f"[Find-LocaAdminAccess] Found {len(entries)} computers in the domain")
			if len(entries) > 100:
				logging.info("[Find-LocalAdminAccess] There are more than 100 computers in the domain. This might take some time")

			for entry in entries:
				try:
					if len(entry['attributes']['dnsHostName']) <= 0:
						continue

					hosts['address'] = host2ip(entry['attributes']['dnsHostName'], self.nameserver, 3, True, use_system_ns=self.use_system_nameserver)
					hosts['hostname'] = entry['attributes']['dnsHostname']
					host_entries.append(hosts.copy())
				except IndexError:
					pass

		local_admin_pcs = []
		for ent in host_entries:
			pc_attr = {}

			if self.use_kerberos:
				smbconn = self.conn.init_smb_session(ent['hostname'])
			else:
				smbconn = self.conn.init_smb_session(ent['address'])

			try:
				smbconn.connectTree("C$")
				pc_attr['attributes'] = {'Name': ent['address'], 'Hostname': ent['hostname']}
				local_admin_pcs.append(pc_attr.copy())
			except:
				pass
		return local_admin_pcs

	def get_regloggedon(self, computer_name, port=445, args=None):
		entries = list()
		if is_ipaddress(computer_name) and self.use_kerberos:
			logging.error("[Get-NetLoggedOn] Use FQDN when using kerberos")
			return

		_rrp = RemoteOperations(
			connection = self.conn,
			port = port
		)
		dce = _rrp.connect(computer_name)

		if not dce:
			logging.error("[Get-RegLoggedOn] Failed to connect to %s" % (computer_name))
			return

		users = _rrp.query_logged_on(dce)
		logging.debug("[Get-RegLoggedOn] Found {} logged on user(s)".format(len(users)))
		for user_sid in users:
			entry = dict({
				"attributes": {
					"ComputerName": computer_name,
					"UserSID": None,
					"UserName": None,
					"UserDomain": None
				}
			})
			entry["attributes"]["UserSID"] = user_sid
			username = self.convertfrom_sid(user_sid)
			if username != user_sid:
				userdomain, username = username.split("\\")
				entry["attributes"]["UserDomain"] = userdomain
				entry["attributes"]["UserName"] = username
			entries.append(entry)

		return entries

	def get_netloggedon(self, computer_name, port=445, args=None):
		KNOWN_PROTOCOLS = {
			139: {'bindstr': r'ncacn_np:%s[\pipe\wkssvc]', 'set_host': True},
			445: {'bindstr': r'ncacn_np:%s[\pipe\wkssvc]', 'set_host': True},
		}

		if is_ipaddress(computer_name) and self.use_kerberos:
			logging.error("[Get-NetLoggedOn] Use FQDN when using kerberos")
			return

		if is_valid_fqdn(computer_name) and not self.use_kerberos:
			computer_name = host2ip(computer_name, self.nameserver, 3, True, use_system_ns=self.use_system_nameserver)

		stringBinding = KNOWN_PROTOCOLS[port]['bindstr'] % computer_name
		dce = self.conn.connectRPCTransport(host=computer_name, stringBindings=stringBinding, interface_uuid = wkst.MSRPC_UUID_WKST)
		
		if not dce:
			logging.error("[Get-NetLoggedOn] Failed to connect to %s" % (computer_name))
			return

		try:
			resp = wkst.hNetrWkstaUserEnum(dce,1)
		except Exception as e:
			if str(e).find('[Get-NetLoggedOn] Broken pipe') >= 0:
				# The connection timed-out. Let's try to bring it back next round
				logging.error('[Get-NetLoggedOn] Connection failed - skipping host!')
				return
			elif str(e).upper().find('ACCESS_DENIED'):
				# We're not admin, bye
				logging.error('[Get-NetLoggedOn] Access denied - you must be admin to enumerate sessions this way')
				dce.disconnect()
				return
			else:
				raise
		try:
			entries = []
			users = set()

			for i in resp['UserInfo']['WkstaUserInfo']['Level1']['Buffer']:
				if i['wkui1_username'][-2] == '$':
					continue
				users.add((host2ip(computer_name, self.nameserver, 3, True, use_system_ns=self.use_system_nameserver), i['wkui1_logon_domain'][:-1], i['wkui1_username'][:-1], i['wkui1_oth_domains'][:-1], i['wkui1_logon_server'][:-1]))
			for user in list(users):
				entries.append({
					"attributes": {
						"UserName": user[2],
						"LogonDomain": user[1],
						"AuthDomains": user[3],
						"LogonServer": user[4],
						"ComputerName": user[0],
					}
				})
		except IndexError:
			logging.info('[Get-NetLoggedOn] No sessions found!')

		dce.disconnect()
		return entries

	def get_netshare(self, args):
		is_fqdn = False
		host = ""
		host_inp = args.computer if args.computer else args.computername

		if host_inp:
			if not is_ipaddress(host_inp):
				is_fqdn = True
				if args.server and args.server.casefold() != self.domain.casefold():
					if not host_inp.endswith(args.server):
						host = f"{host_inp}.{args.server}"
					else:
						host = host_inp
				else:
					if not is_valid_fqdn(host_inp):
						host = f"{host_inp}.{self.domain}"
					else:
						host = host_inp
				logging.debug(f"[Get-NetShare] Using FQDN: {host}")
			else:
				host = host_inp

		if self.use_kerberos:
			if is_ipaddress(args.computer) or is_ipaddress(args.computername):
				logging.error('[Get-NetShare] FQDN must be used for kerberos authentication')
				return
		else:
			if is_fqdn:
				host = host2ip(host, self.nameserver, 3, True, use_system_ns=self.use_system_nameserver)

		if not host:
			logging.error(f"[Get-NetShare] Host not found")
			return

		client = self.conn.init_smb_session(host)

		if not client:
			logging.error("[Get-NetShare] Failed to connect to %s" % (host))
			return
		
		smbclient = SMBClient(client)
		shares = smbclient.shares()
		entries = []
		for i in range(len(shares)):
			entry = {
				"Name": None,
				"Remark": None,
				"Address": None,
			}
			entry["Name"] = shares[i]['shi1_netname'][:-1]
			entry["Remark"] = shares[i]['shi1_remark'][:-1]
			entry["Address"] = host
			entries.append(
				{
					"attributes": dict(entry)
				}
			)

		return entries

	def remove_netservice(self,
		computer_name,
		service_name,
		port=445
	):
		if not computer_name or not service_name:
			if self.args.stack_trace:
				raise ValueError("[Remove-NetService] Computer name, service name, and path are required")
			else:
				logging.error("[Remove-NetService] Computer name, service name, and path are required")
				return False

		service_name = service_name + '\x00' if service_name else NULL

		KNOWN_PROTOCOLS = {
			139: {'bindstr': r'ncacn_np:%s[\pipe\svcctl]', 'set_host': True},
			445: {'bindstr': r'ncacn_np:%s[\pipe\svcctl]', 'set_host': True},
		}

		stringBinding = KNOWN_PROTOCOLS[port]['bindstr'] % computer_name
		dce = self.conn.connectRPCTransport(host=computer_name, stringBindings=stringBinding)

		if not dce:
			logging.error("[Set-NetService] Failed to connect to %s" % (computer_name))
			return False

		dce.bind(scmr.MSRPC_UUID_SCMR)

		try:
			res = scmr.hROpenSCManagerW(dce)
			scManagerHandle = res['lpScHandle']

			logging.debug(f"[Remove-NetService] Opening service handle {service_name} on {computer_name}")
			resp = scmr.hROpenServiceW(dce, scManagerHandle, service_name)
			serviceHandle = resp['lpServiceHandle']

			scmr.hRDeleteService(dce, serviceHandle)
			logging.info(f"[Remove-NetService] Service {service_name} removed from {computer_name}")

			logging.debug(f"[Remove-NetService] Closing service handle {service_name} on {computer_name}")
			scmr.hRCloseServiceHandle(dce, scManagerHandle)
			dce.disconnect()
			return True
		except Exception as e:
			logging.error("[Remove-NetService] %s" % (str(e)))
			return False

	def stop_netservice(self,
		computer_name,
		service_name,
		port=445
	):
		if not computer_name or not service_name:
			if self.args.stack_trace:
				raise ValueError("[Stop-NetService] Computer name, service name, and path are required")
			else:
				logging.error("[Stop-NetService] Computer name, service name, and path are required")
				return False

		service_name = service_name + '\x00' if service_name else NULL

		KNOWN_PROTOCOLS = {
			139: {'bindstr': r'ncacn_np:%s[\pipe\svcctl]', 'set_host': True},
			445: {'bindstr': r'ncacn_np:%s[\pipe\svcctl]', 'set_host': True},
		}

		stringBinding = KNOWN_PROTOCOLS[port]['bindstr'] % computer_name
		dce = self.conn.connectRPCTransport(host=computer_name, stringBindings=stringBinding)

		if not dce:
			logging.error("[Set-NetService] Failed to connect to %s" % (computer_name))
			return False

		dce.bind(scmr.MSRPC_UUID_SCMR)

		try:
			res = scmr.hROpenSCManagerW(dce)
			scManagerHandle = res['lpScHandle']

			logging.debug(f"[Stop-NetService] Opening service handle {service_name} on {computer_name}")
			resp = scmr.hROpenServiceW(dce, scManagerHandle, service_name)
			serviceHandle = resp['lpServiceHandle']

			scmr.hRControlService(dce, serviceHandle, scmr.SERVICE_CONTROL_STOP)
			logging.info(f"[Stop-NetService] Service {service_name} stopped on {computer_name}")

			logging.debug(f"[Stop-NetService] Closing service handle {service_name} on {computer_name}")
			scmr.hRCloseServiceHandle(dce, serviceHandle)
			scmr.hRCloseServiceHandle(dce, scManagerHandle)
			dce.disconnect()
			return True
		except Exception as e:
			raise ValueError("[Stop-NetService] %s" % (str(e)))

	def start_netservice(self,
		computer_name,
		service_name,
		port=445
	):
		if not computer_name or not service_name:
			if self.args.stack_trace:
				raise ValueError("[Start-NetService] Computer name, service name, and path are required")
			else:
				logging.error("[Start-NetService] Computer name, service name, and path are required")
				return False

		service_name = service_name + '\x00' if service_name else NULL

		KNOWN_PROTOCOLS = {
			139: {'bindstr': r'ncacn_np:%s[\pipe\svcctl]', 'set_host': True},
			445: {'bindstr': r'ncacn_np:%s[\pipe\svcctl]', 'set_host': True},
		}

		stringBinding = KNOWN_PROTOCOLS[port]['bindstr'] % computer_name
		dce = self.conn.connectRPCTransport(host=computer_name, stringBindings=stringBinding)

		if not dce:
			logging.error("[Set-NetService] Failed to connect to %s" % (computer_name))
			return False

		dce.bind(scmr.MSRPC_UUID_SCMR)

		try:
			res = scmr.hROpenSCManagerW(dce)
			scManagerHandle = res['lpScHandle']

			logging.debug(f"[Start-NetService] Opening service handle {service_name} on {computer_name}")
			resp = scmr.hROpenServiceW(dce, scManagerHandle, service_name)
			serviceHandle = resp['lpServiceHandle']

			scmr.hRStartServiceW(dce, serviceHandle)
			logging.info(f"[Start-NetService] Service {service_name} started on {computer_name}")

			logging.debug(f"[Start-NetService] Closing service handle {service_name} on {computer_name}")
			scmr.hRCloseServiceHandle(dce, serviceHandle)
			scmr.hRCloseServiceHandle(dce, scManagerHandle)
			dce.disconnect()
			return True
		except Exception as e:
			raise ValueError("[Start-NetService] %s" % (str(e)))

	def add_netservice(self,
		computer_name,
		service_name,
		display_name,
		binary_path,
		service_type=None,
		start_type=None,
		error_control=None,
		service_start_name=None,
		password=None,
		port=445
	):

		if not computer_name or not service_name:
			if self.args.stack_trace:
				raise ValueError("[Add-NetService] Computer name, service name, and path are required")
			else:
				logging.error("[Add-NetService] Computer name, service name, and path are required")
				return False

		service_name = service_name + '\x00' if service_name else NULL
		display_name = display_name + '\x00' if display_name else NULL
		binary_path = binary_path + '\x00' if binary_path else NULL
		service_type = int(service_type) if service_type else scmr.SERVICE_WIN32_OWN_PROCESS
		start_type = int(start_type) if start_type else scmr.SERVICE_AUTO_START
		error_control = int(error_control) if error_control else scmr.SERVICE_ERROR_IGNORE
		service_start_name = service_start_name + '\x00' if service_start_name else NULL
		if password:
			client = self.conn.init_smb_session(computer_name)
			key = client.getSessionKey()
			try:
				password = (password+'\x00').encode('utf-16le')
			except UnicodeDecodeError:
				import sys
				password = (password+'\x00').decode(sys.getfilesystemencoding()).encode('utf-16le')
			password = encryptSecret(key, password)
		else:
			password = NULL

		KNOWN_PROTOCOLS = {
			139: {'bindstr': r'ncacn_np:%s[\pipe\svcctl]', 'set_host': True},
			445: {'bindstr': r'ncacn_np:%s[\pipe\svcctl]', 'set_host': True},
		}

		stringBinding = KNOWN_PROTOCOLS[port]['bindstr'] % computer_name
		dce = self.conn.connectRPCTransport(host=computer_name, stringBindings=stringBinding)

		if not dce:
			logging.error("[Set-NetService] Failed to connect to %s" % (computer_name))
			return False

		dce.bind(scmr.MSRPC_UUID_SCMR)

		try:
			res = scmr.hROpenSCManagerW(dce)
			scManagerHandle = res['lpScHandle']

			scmr.hRCreateServiceW(
				dce,
				scManagerHandle,
				service_name,
				display_name,
				dwServiceType=service_type,
				dwStartType=start_type,
				dwErrorControl=error_control,
				lpBinaryPathName=binary_path,
				lpServiceStartName=service_start_name,
				lpPassword=password
			)
			logging.info(f"[Add-NetService] Service {service_name} added to {computer_name}")

			logging.debug(f"[Add-NetService] Closing service handle {service_name} on {computer_name}")
			scmr.hRCloseServiceHandle(dce, scManagerHandle)
			dce.disconnect()
			return True
		except Exception as e:
			raise ValueError("[Add-NetService] %s" % (str(e)))

	def set_netservice(self,
		computer_name,
		service_name,
		display_name=None,
		binary_path=None,
		service_type=None,
		start_type=None,
		error_control=None,
		service_start_name=None,
		password=None,
		port=445
	):
		if not computer_name or not service_name:
			if self.args.stack_trace:
				raise ValueError("[Set-NetService] Computer name, service name, and path are required")
			else:
				logging.error("[Set-NetService] Computer name, service name, and path are required")
				return False

		KNOWN_PROTOCOLS = {
			139: {'bindstr': r'ncacn_np:%s[\pipe\svcctl]', 'set_host': True},
			445: {'bindstr': r'ncacn_np:%s[\pipe\svcctl]', 'set_host': True},
		}

		stringBinding = KNOWN_PROTOCOLS[port]['bindstr'] % computer_name
		dce = self.conn.connectRPCTransport(host=computer_name, stringBindings=stringBinding)

		if not dce:
			logging.error("[Set-NetService] Failed to connect to %s" % (computer_name))
			return False

		dce.bind(scmr.MSRPC_UUID_SCMR)

		try:
			res = scmr.hROpenSCManagerW(dce)
			scManagerHandle = res['lpScHandle']

			# Open service handle
			logging.debug(f"[Set-NetService] Opening service handle {service_name} on {computer_name}")
			resp = scmr.hROpenServiceW(dce, scManagerHandle, service_name + '\x00')
			serviceHandle = resp['lpServiceHandle']

			display = display_name + '\x00' if display_name else NULL
			binary_path = binary_path + '\x00' if binary_path else NULL
			service_type = service_type if service_type else scmr.SERVICE_NO_CHANGE
			start_type = start_type if start_type else scmr.SERVICE_NO_CHANGE
			error_control = error_control if error_control else scmr.SERVICE_ERROR_IGNORE
			service_start_name = service_start_name + '\x00' if service_start_name else NULL
			if password:
				client = self.conn.init_smb_session(computer_name)
				key = client.getSessionKey()
				try:
					password = (password+'\x00').encode('utf-16le')
				except UnicodeDecodeError:
					import sys
					password = (password+'\x00').decode(sys.getfilesystemencoding()).encode('utf-16le')
				password = encryptSecret(key, password)
			else:
				password = NULL

			logging.debug(f"[Set-NetService] Changing service config {service_name} on {computer_name}")

			scmr.hRChangeServiceConfigW(
				dce, 
				serviceHandle,
				service_type,
				start_type,
				error_control,
				binary_path,
				NULL,
				NULL,
				NULL,
				0,
				service_start_name,
				password,
				0,
				display
			)
			logging.info(f"[Set-NetService] Service config changed {service_name} on {computer_name}")

			logging.debug(f"[Set-NetService] Closing service handle {service_name} on {computer_name}")
			scmr.hRCloseServiceHandle(dce, serviceHandle)
			scmr.hRCloseServiceHandle(dce, scManagerHandle)
			dce.disconnect()

			return True
		except Exception as e:
			raise ValueError("[Set-NetService] %s" % (str(e)))

	def get_netservice(self,
		computer_name,
		port=445,
		name=None,
		is_running=None,
		is_stopped=None,
		raw=False
	):

		KNOWN_PROTOCOLS = {
			139: {'bindstr': r'ncacn_np:%s[\pipe\svcctl]', 'set_host': True},
			445: {'bindstr': r'ncacn_np:%s[\pipe\svcctl]', 'set_host': True},
		}


		stringBinding = KNOWN_PROTOCOLS[port]['bindstr'] % computer_name
		dce = self.conn.connectRPCTransport(host=computer_name, stringBindings=stringBinding)
		
		if not dce:
			logging.error("[Get-NetService] Failed to connect to %s" % (computer_name))
			return False

		dce.bind(scmr.MSRPC_UUID_SCMR)

		try:
			# open service handle
			res = scmr.hROpenSCManagerW(dce)
			scManagerHandle = res['lpScHandle']

			if name:
				ans = scmr.hROpenServiceW(dce, scManagerHandle, name + '\x00')
				serviceHandle = ans['lpServiceHandle']

				config = {}
				logging.debug(f"[Get-NetService] Querying service config for {name} on {computer_name}")
				resp = scmr.hRQueryServiceConfigW(dce, serviceHandle)
				config['attributes'] = {}
				config['attributes']['ServiceName'] = name
				config['attributes']['DisplayName'] = resp['lpServiceConfig']['lpDisplayName'][:-1]
				config['attributes']['StartType'] = SERVICE_START_TYPE(resp['lpServiceConfig']['dwStartType']).to_str() if not raw else resp['lpServiceConfig']['dwStartType']
				config['attributes']['ErrorControl'] = SERVICE_ERROR_CONTROL(resp['lpServiceConfig']['dwErrorControl']).to_str() if not raw else resp['lpServiceConfig']['dwErrorControl']
				config['attributes']['BinaryPath'] = resp['lpServiceConfig']['lpBinaryPathName'][:-1] if not raw else resp['lpServiceConfig']['lpBinaryPathName']
				config['attributes']['ServiceType'] = SERVICE_TYPE(resp['lpServiceConfig']['dwServiceType']).to_str() if not raw else resp['lpServiceConfig']['dwServiceType']
				config['attributes']['Dependencies'] = resp['lpServiceConfig']['lpDependencies'][:-1]
				config['attributes']['ServiceStartName'] = resp['lpServiceConfig']['lpServiceStartName'][:-1]

				logging.debug(f"[Get-NetService] Querying service status for {name} on {computer_name}")
				resp = scmr.hRQueryServiceStatus(dce, serviceHandle)
				config['attributes']['Status'] = SERVICE_STATUS(resp['lpServiceStatus']['dwCurrentState']).to_str() if not raw else resp['lpServiceStatus']['dwCurrentState']
				config['attributes']['Win32ExitCode'] = SERVICE_WIN32_EXIT_CODE(resp['lpServiceStatus']['dwWin32ExitCode']).to_str() if not raw else resp['lpServiceStatus']['dwWin32ExitCode']
				config['attributes']['ServiceSpecificExitCode'] = resp['lpServiceStatus']['dwServiceSpecificExitCode']
				config['attributes']['CheckPoint'] = resp['lpServiceStatus']['dwCheckPoint']
				config['attributes']['WaitHint'] = resp['lpServiceStatus']['dwWaitHint']

				return [config]
			else:
				resp = scmr.hREnumServicesStatusW(dce, scManagerHandle)

		except Exception as e:
			raise ValueError("[Get-NetService] %s" % (str(e)))

		edr = EDR()
		entries = []
		
		try:
			for i in range(len(resp)):
				state = resp[i]['ServiceStatus']['dwCurrentState']
				service_name = resp[i]['lpServiceName'][:-1]
				displayname = resp[i]['lpDisplayName'][:-1]

				if is_running and not state == scmr.SERVICE_RUNNING:
					continue
				elif is_stopped and not state == scmr.SERVICE_STOPPED:
					continue

				if edr.service_exist(service_name):
					service_name = f"{bcolors.WARNING}{service_name}{bcolors.ENDC}"
					displayname = f"{bcolors.WARNING}{displayname}{bcolors.ENDC}"

				entry = {
					"Name": service_name,
					"DisplayName": displayname,
					"Status": "UNKNOWN",
				}
				if state == scmr.SERVICE_CONTINUE_PENDING:
				   entry["Status"] = "CONTINUE PENDING"
				elif state == scmr.SERVICE_PAUSE_PENDING:
				   entry["Status"] = "PAUSE PENDING"
				elif state == scmr.SERVICE_PAUSED:
					entry["Status"] = "PAUSED"
				elif state == scmr.SERVICE_RUNNING:
				   entry["Status"] = f"{bcolors.OKGREEN}RUNNING{bcolors.ENDC}"
				elif state == scmr.SERVICE_START_PENDING:
				   entry["Status"] = "START PENDING"
				elif state == scmr.SERVICE_STOP_PENDING:
				   entry["Status"] = "STOP PENDING"
				elif state == scmr.SERVICE_STOPPED:
				   entry["Status"] = f"{bcolors.FAIL}STOPPED{bcolors.ENDC}"

				entries.append(
					{
						"attributes": dict(entry)
					}
				)

			logging.debug("[Get-NetService] Total services found: %d" % len(resp))
		except IndexError:
			logging.error("[Get-NetService] Error enumerating service")
			return

		dce.disconnect()
		return entries

	def get_netsession(self, identity=None, port=445, args=None):
		KNOWN_PROTOCOLS = {
			139: {'bindstr': r'ncacn_np:%s[\pipe\srvsvc]', 'set_host': True},
			445: {'bindstr': r'ncacn_np:%s[\pipe\srvsvc]', 'set_host': True},
		}

		if is_ipaddress(identity) and self.use_kerberos:
			logging.error("[Get-NetSession] Use FQDN when using kerberos")
			return

		if is_valid_fqdn(identity) and not self.use_kerberos:
			identity = host2ip(identity, self.nameserver, 3, True, use_system_ns=self.use_system_nameserver)

		stringBinding = KNOWN_PROTOCOLS[port]['bindstr'] % identity
		dce = self.conn.connectRPCTransport(host=identity, stringBindings=stringBinding, interface_uuid = srvs.MSRPC_UUID_SRVS)

		if dce is None:
			logging.error("[Get-NetSession] Failed to connect to %s" % (identity))
			return

		try:
			resp = srvs.hNetrSessionEnum(dce, '\x00', NULL, 10)
		except Exception as e:
			if 'rpc_s_access_denied' in str(e):
				logging.info('Access denied while enumerating Sessions on %s' % (identity))
			else:
				logging.info(str(e))
			return

		sessions = []
		for session in resp['InfoStruct']['SessionInfo']['Level10']['Buffer']:
			ip = session['sesi10_cname'][:-1]
			userName = session['sesi10_username'][:-1]
			time = session['sesi10_time']
			idleTime = session['sesi10_idle_time']

			if userName[:-1] == "$":
				continue

			sessions.append({
				"attributes": {
					"IP": ip,
					"Username": userName,
					"Time": time,
					"Idle Time": idleTime,
					"Computer": identity,
					}
				})

		return sessions
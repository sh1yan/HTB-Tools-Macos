import datetime
from dateutil.relativedelta import relativedelta

from impacket.uuid import bin_to_string
from ldap3.protocol.formatters.formatters import format_sid

from powerview.modules.gmsa import GMSA
from powerview.utils.constants import (
	UAC_DICT,
	LDAP_ERROR_STATUS,
	SUPPORTED_sAMAccountType,
	SUPPORTED_ENCRYPTION_TYPES,
	switcher_trustDirection,
	switcher_trustType,
	switcher_trustAttributes,
	PWD_FLAGS,
)

class UAC:
	@staticmethod
	def parse_value(uac_value):
		uac_value = int(uac_value)
		flags = []

		for key, value in UAC_DICT.items():
			if uac_value & key:
				flags.append(value)

		return flags

	@staticmethod
	def parse_value_tolist(uac_value):
		uac_value = int(uac_value)
		flags = []

		for key, value in UAC_DICT.items():
			if uac_value & key:
				flags.append([value, key])

		return flags

class ENCRYPTION_TYPE:
	@staticmethod
	def parse_value(enc_value):
		enc_value = int(enc_value)
		flags = []

		for key, value in SUPPORTED_ENCRYPTION_TYPES.items():
			if enc_value & key:
				flags.append(value)

		return flags

class sAMAccountType:
	@staticmethod
	def parse_value(enc_value):
		enc_value = int(enc_value)

		if enc_value in SUPPORTED_sAMAccountType:
			return SUPPORTED_sAMAccountType[enc_value]
		else:
			return env_value

class LDAP:
	@staticmethod
	def resolve_err_status(error_status):
		return LDAP_ERROR_STATUS.get(error_status)

	@staticmethod
	def resolve_enc_type(enc_type):
		if isinstance(enc_type, list):
			return ENCRYPTION_TYPE.parse_value(enc_type[0])
		elif isinstance(enc_type, bytes):
			return ENCRYPTION_TYPE.parse_value(enc_type.decode())
		else:
			return ENCRYPTION_TYPE.parse_value(enc_type)

	@staticmethod
	def resolve_samaccounttype(enc_type):
		if isinstance(enc_type, list):
			return sAMAccountType.parse_value(enc_type[0])
		elif isinstance(enc_type, bytes):
			return sAMAccountType.parse_value(enc_type.decode())
		else:
			return sAMAccountType.parse_value(enc_type)

	@staticmethod
	def resolve_uac(uac_val):
		# resolve userAccountControl
		if isinstance(uac_val, list):
			val =  UAC.parse_value(uac_val[0])
		elif isinstance(uac_val, bytes):
			val = UAC.parse_value(uac_val.decode())
		else:
			val = UAC.parse_value(uac_val)

		val[0] = f"{val[0]} [{uac_val.decode()}]"

		return val

	@staticmethod
	def parse_uac_name_to_value(uac_names, delimiter=','):
		"""Convert UAC flag names to numeric value
		Args:
			uac_names (str): Comma-separated UAC flag names
		Returns:
			int: Combined UAC numeric value
		"""
		if not uac_names:
			return 0
			
		uac_value = 0
		names = [name.strip() for name in uac_names.split(delimiter)]
		
		# Create reverse mapping of name->value
		reverse_uac = {value: key for key, value in UAC_DICT.items()}
		
		for name in names:
			if name in reverse_uac:
				uac_value |= reverse_uac[name]
				
		return uac_value

	@staticmethod
	def ldap2datetime(ts):
		if isinstance(ts, datetime.datetime):
			return ts
		else:
			ts = int(ts)
			dt = datetime.datetime(1601, 1, 1) + datetime.timedelta(seconds=ts / 10000000)
		#return datetime.datetime(1601, 1, 1) + datetime.timedelta(seconds=ts/10000000)
		return f"{dt.strftime('%d/%m/%Y %H:%M:%S')} ({LDAP.human_readable_time_diff(dt)})"

	@staticmethod
	def human_readable_time_diff(past_date):
		now = datetime.datetime.now()
		diff = relativedelta(now, past_date)

		if diff.years > 0:
			return f"{diff.years} year{'s' if diff.years > 1 else ''}, {diff.months} month{'s' if diff.months > 1 else ''} ago"
		elif diff.months > 0:
			return f"{diff.months} month{'s' if diff.months > 1 else ''}, {diff.days} day{'s' if diff.days > 1 else ''} ago"
		elif diff.days > 0:
			return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
		else:
			return "today"

	@staticmethod
	def resolve_generalized_time(ldap_time):
		if isinstance(ldap_time, datetime.datetime):
			dt = ldap_time
		else:
			if isinstance(ldap_time, bytes):
				ldap_time = ldap_time.decode()
			dt = datetime.datetime.strptime(ldap_time, "%Y%m%d%H%M%S.%fZ")
		
		return f"{dt.strftime('%d/%m/%Y %H:%M:%S')} ({LDAP.human_readable_time_diff(dt)})"

	@staticmethod
	def bin_to_guid(guid):
		return "{%s}" % bin_to_string(guid).lower()

	@staticmethod
	def bin_to_sid(sid):
		return format_sid(sid)

	@staticmethod
	def formatGMSApass(managedPassword):
		return GMSA.decrypt(managedPassword)

	@staticmethod
	def parseGMSAMembership(secDesc):
		return GMSA.read_acl(secDesc)

	@staticmethod
	def resolve_pwdProperties(flag):
		prop =  PWD_FLAGS.get(int(flag))
		return f"({flag.decode()}) {prop}" if prop else flag

class TRUST:
	@staticmethod
	def resolve_trustDirection(flag):
		flag = int(flag)
		types = []
		for bit, name in switcher_trustDirection.items():
			if flag & bit:
				types.append(name)
		return types

	@staticmethod
	def resolve_trustType(flag):
		flag = int(flag)
		types = []
		for bit, name in switcher_trustType.items():
			if flag & bit:
				types.append(name)
		return types

	@staticmethod
	def resolve_trustAttributes(flag):
		flag = int(flag)
		attributes = []
		for bit, name in switcher_trustAttributes.items():
			if flag & bit:
				attributes.append(name)
		return attributes

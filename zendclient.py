"""
Implementation of (a good part of) Zend Server web API.

Doc: http://files.zend.com/help/Zend-Server/content/web_api_reference_guide.htm
"""

import requests
import time
import hmac
import hashlib
import xmltodict
import zipfile
import urllib.parse
from requests_toolbelt.multipart.encoder import MultipartEncoder

class ZendClient:
	xmlnamespace = {'zend': 'http://www.zend.com/server/deployment-descriptor/1.0',
					'zendapi': 'http://www.zend.com/server/api/1.11'}

	def __init__(self):
		print ('Debug: Init zendclient class')
		self.__host = "127.0.0.1:10081"
		self.__key = "admin"
		self.__hash = "secret"
		self.__useragent = "zend_http_client"

	def __repr__(self):
		return "ZendClient(host=%r, key=%r, hash=%r, useragent=%r)" %   \
					(self.__host, self.__key, self.__hash, self.__useragent)


	def application_deploy(self,parameters=[]):
		"""
		Allow to deploy a new package in the current ZendServer instance.
		This function expect all the parameter to be set correctly as described in the Zend Documentation
		and only act as a Wrapper. The data should be sent as a list object containing tuple.

		:param parameters: List containing tuple of all the parameters required to deploy. See: http://files.zend.com/help/Zend-Server/content/the_applicationdeploy_method.htm for the complete list

		"""
		multipart_data = MultipartEncoder(parameters)
		response = self.do_request("/ZendServer/Api/applicationDeploy",multipart_data=multipart_data)
		return self.wait_for_deployment(xmltodict.parse(response.text))

	def get_package_metadata(self,filename):
		"""
		Read the deployment file inside the ZPK provided in argument in order to generate the configuration. 
		The configuration generated is compliant with the class alphanetworks.Configuration. And will use the package name
		as section name.

		The configuration is pre-filled based on the default value in the xml.

		:param filename: The path to the ZPK file used to generate the configuration

		"""
		archive = zipfile.ZipFile(filename, 'r')
		xmldata = archive.read('deployment.xml')

		package_config=xmltodict.parse(xmldata)
		return {'filename':filename,'packagename':package_config['package']['name'],'packageversion':package_config['package']['version']['release']}

	def get_package_configuration(self,filename):
		"""
		Read the deployment file inside the ZPK provided in argument in order to generate the configuration. 
		The configuration generated is compliant with the class alphanetworks.Configuration. And will use the package name
		as section name.

		The configuration is pre-filled based on the default value in the xml.

		:param filename: The path to the ZPK file used to generate the configuration

		"""
		archive = zipfile.ZipFile(filename, 'r')
		xmldata = archive.read('deployment.xml')

		package_config=xmltodict.parse(xmldata)

		if 'parameters' not in package_config['package'] or package_config['package']['parameters'] is None:
			return {'package_name':package_config['package']['name'],'configuration':[]}

		configuration=[]
		for parameter in package_config['package']['parameters']['parameter']:
			configuration.append({parameter['@id']:('' if 'defaultvalue' not in parameter or parameter['defaultvalue'] is None else parameter['defaultvalue'])})
		return {'package_name':package_config['package']['name'],'configuration':configuration}


	def jobqueue_get_queues(self):
		response = self.do_request('/ZendServer/Api/jobqueueGetQueues')
		return xmltodict.parse(response.text)

	def get_jobqueue_config(self):
		configuration={'job_queues':[]}
		for queue in self.jobqueue_get_queues()['zendServerAPIResponse']['responseData']['queues']['queue']:
			queueconfig = '{'
			queueconfig+='"priority":'+queue['priority']
			queueconfig+=',"max_http_jobs":'+queue['max_http_jobs']
			queueconfig+=',"max_wait_time":'+queue['max_wait_time']
			queueconfig+=',"http_connection_timeout":'+queue['http_connection_timeout']
			queueconfig+=',"http_job_timeout":'+queue['http_job_timeout']
			queueconfig+=',"http_job_retry_count":'+queue['http_job_retry_count']
			queueconfig+=',"http_job_retry_timeout":'+queue['http_job_retry_timeout']
			queueconfig+='}'
			configuration['job_queues'].append({'name':queue['name'],'value':queueconfig})
		return configuration
		
	def generate_signature(self,uri,timestamp):
		"""
		Generate signature as described in ZendApi documentation

		:param uri: Zend url with the port but without http
		:param timestamp: timestamp that will be used in the request..

		"""
		data=self.__host+':'+uri.split('?')[0]+':'+self.__useragent+':'+timestamp
		return hmac.new(self.__hash.encode('ascii'), data.encode('ascii'), hashlib.sha256).hexdigest()

	def set_target(self,data):
		self.__host=data['host']
		self.__key=data['key']
		self.__hash=data['hash']

	def do_request(self,uri,data=None,multipart_data=None, files=None):
		timestamp = time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime())
		headers= {'Date': timestamp,
				  'User-agent': self.__useragent,
				  'X-Zend-Signature': self.__key+'; '+ self.generate_signature(uri,timestamp),
				  'Accept':'application/vnd.zend.serverapi+xml;version=1.9'}

		if files is not None:
			response = requests.post('http://'+self.__host+uri, files=files, headers=headers)
		elif multipart_data is not None:
			headers['Content-Type']= multipart_data.content_type
			response = requests.post('http://'+self.__host+uri, data=multipart_data,headers=headers)
		elif data is not None:
			response = requests.post('http://'+self.__host+uri, data=data,headers=headers)
		else:
			response = requests.get('http://'+self.__host+uri,headers=headers)
		return response


	def lib_version_deploy(self, name, path):
		"""
		Deploy a new library version to the server or cluster. 
		This process is asynchronous – the initial request will wait until the
		library is uploaded and verified, and the initial response will show 
		information about the library being deployed – however the staging and 
		activation process will proceed after the response is returned. 
		The user is expected to continue checking the library version status
		using the libraryVersionGetStatus method until the deployment process is
		complete.

		http://files.zend.com/help/Zend-Server/content/the_libraryversiondeploy_method.htm
		"""
		lib_file_param = {
			'libPackage': (name, open(path+name, 'rb').read(), 'library/vnd.zend.librarypackage')
		}
		
		response = self.do_request("/ZendServer/Api/libraryVersionDeploy", files=lib_file_param)
		return xmltodict.parse(response.text)

	def lib_version_synchronize(self, lib_version_id):
		"""
		Cause the library version to be deployed again from its original package 
		file. This can be used to cause the library to deploy in a cluster on 
		members that are missing files or the library was not deployed at all 
		on them.

		http://files.zend.com/help/Zend-Server/content/the_librarysynchronize_method.htm
		"""
		data = {
			libraryVersionId: lib_version_id
		}
		response = self.do_request("/ZendServer/Api/libraryVersionSynchronize", data=data)
		return xmltodict.parse(response.text)

	def lib_version_get_status(self, lib_version_id):
		"""
		Get the library version ID that is deployed on the server or the
		cluster, and information about that version and its library.

		http://files.zend.com/help/Zend-Server/content/the_libraryversiongetstatus_method.htm
		"""
		response = self.do_request("/ZendServer/Api/libraryVersionGetStatus?libraryVersionId="+lib_version_id)
		return xmltodict.parse(response.text)


	def lib_get_status(self, libraries=None, direction=None):
		"""
		Get the list of libraries currently deployed on the server or the
		cluster, and information about each library’s available versions.
		If library IDs are specified, will return information about the 
		specified applications; If no IDs are specified, will return 
		information about all libraries.

		http://files.zend.com/help/Zend-Server/content/the_librarygetstatus_method.htm		
		"""
		query_params = []

		if libraries is not None:
			query_string = "&".join([ "libraries[]=%r" % (lib_id) for lib_id in libraries ])
			query_params.append(query_string)

		if direction is not None and direction in ["ASC", "DESC"]:
			query_params.append("direction=%s" % (direction,))

		response = self.do_request("/ZendServer/Api/libraryGetStatus?" + "&".join(query_params))
		return xmltodict.parse(response.text)



	def application_get_status(self,applicationid=None):
		response = self.do_request('/ZendServer/Api/applicationGetStatus'+('?applications[]='+str(applicationid) if applicationid is not None else ''))
		return xmltodict.parse(response.text)


	#Retrieve in a prettier way the application getStatus
	def get_application_list(self):
		applicationlist = []
		response = self.application_get_status()
		if (response['zendServerAPIResponse']['responseData']['applicationsList'] is None):
			return []
		application_info = response['zendServerAPIResponse']['responseData']['applicationsList']['applicationInfo']
		if (type(application_info) is not list):
			application_info=[application_info]
		for information in application_info:
			version=[]
			application_server=information['servers']['applicationServer']
			if (type(application_server) is not list):
				application_server=[application_server]
			for servers in application_server:
				version.append({'version':servers['deployedVersion'],'server':servers['id']})
			applicationlist.append({'id':information['id'],
									'packagename':information['appName'],
									'baseurl':information['baseUrl'],
									'displayname':information['userAppName'],
									'version':version})

		return applicationlist

	def application_get_details(self,applicationid):
		response = self.do_request("/ZendServer/Api/applicationGetDetails?application="+str(applicationid))
		return xmltodict.parse(response.text.replace("&","&amp;"))


	def get_applications_config(self,applicationid=None):
		configuration={}
		applicationlist=[]

		if (applicationid is None):
			for application in self.get_application_list():
				applicationlist.append(application['id'])
		else:
			applicationlist.append(applicationid)

		for application in applicationlist:
			response = self.application_get_details(application)
			packagename=response['zendServerAPIResponse']['responseData']['applicationDetails']['applicationInfo']['appName']
			configuration[packagename]=[]

			if response['zendServerAPIResponse']['responseData']['applicationDetails']['applicationPackage']['userParams'] is not None:
				for information in response['zendServerAPIResponse']['responseData']['applicationDetails']['applicationPackage']['userParams']['parameter']:
					configuration[packagename].append({'name':information['name'],'value':( '' if information['value'] is None else information['value'] )})
			configuration[packagename].append({'name':'metadata_baseurl','value':response['zendServerAPIResponse']['responseData']['applicationDetails']['applicationInfo']['baseUrl']})
			configuration[packagename].append({'name':'metadata_displayname','value':response['zendServerAPIResponse']['responseData']['applicationDetails']['applicationInfo']['userAppName']})
		return configuration


	def vhost_get_status(self):
		response = self.do_request("/ZendServer/Api/vhostGetStatus")
		return (xmltodict.parse(response.text))

	def get_vhost_list(self):
		vhostlist=[]

		response = self.vhost_get_status()
		for information in response['zendServerAPIResponse']['responseData']['vhostList']['vhostInfo']:
			status=[]
			if (type(information['servers']['vhostServer']) == list):
				for servers in information['servers']['vhostServer']:
					status.append({'id':servers['id'],'status':servers['status']})
			else:
				status.append({'id':information['servers']['vhostServer']['id'],'status':information['servers']['vhostServer']['status']})
			vhostlist.append({'id':information['id'],'baseurl':information['name'],'status':status})
		return vhostlist

	def vhost_get_details(self,vhostid):
		response = self.do_request("/ZendServer/Api/vhostGetDetails?vhost="+str(vhostid))
		return (xmltodict.parse(response.text))

	def get_vhost_config(self,vhostid=None):
		configuration={}
		vhostlist=[]

		if (vhostid is None):
			for vhost in self.get_vhost_list():
				vhostlist.append(vhost['id'])
		else:
			vhostlist.append(vhostid)

		for vhost in vhostlist:
			response = self.vhost_get_details(vhost)
			vhostname=response['zendServerAPIResponse']['responseData']['vhostDetails']['vhostInfo']['name']
			configuration[vhostname]=[{'name': 'template','value':('' if response['zendServerAPIResponse']['responseData']['vhostDetails']['vhostExtended']['template'] is None else response['zendServerAPIResponse']['responseData']['vhostDetails']['vhostExtended']['template'])}]
		return configuration

	def vhost_edit(self,vhostid,template):
		data = {'vhostId':vhostid,'template':template}
		response = self.do_request("/ZendServer/Api/vhostEdit",data=data)
		return xmltodict.parse(response.text)

	def vhost_redeploy(self,vhostid):
		data = {'vhost':vhostid}
		response = self.do_request("/ZendServer/Api/vhostRedeploy",data=data)
		return xmltodict.parse(response.text)

	def synchronize_vhost(self,templates):
		require_restart = False
		for vhost in self.get_vhost_list():
			require_redeploy=False
			for servers in vhost['status']:
				if servers['status'] == 'Modified':
					print ("vHost has been modified on Disk on server "+servers['id']+"! Reverting to configured value")
					require_redeploy=True
			if require_redeploy:
				self.vhost_redeploy(vhost['id'])
				require_restart=True
			if (vhost['baseurl'] in templates):
				current_template = self.get_vhost_config(vhost['id'])[vhost['baseurl']][0]['value'].rstrip().lstrip()
				configuration_template = (templates[vhost['baseurl']][0]['value']).rstrip().lstrip()
				if (current_template != configuration_template):
					print ("Sync in progress: "+vhost['baseurl']+' ('+vhost['id']+')')
					self.vhost_edit(vhost['id'],configuration_template)
					require_restart=True
		if (require_restart):
			self.restart_php()
		#print (templates)

	def restart_php(self):
		print ("Restarting: PHP", end='', flush=True)
		data = {'force':'FALSE'}
		response = self.do_request("/ZendServer/Api/restartPhp",data=data)
		self.wait_for_task_complete()
		return xmltodict.parse(response.text)

	def configuration_directives_list(self):
		response = self.do_request("/ZendServer/Api/configurationDirectivesList")
		return xmltodict.parse(response.text)

	def configuration_extensions_list(self):
		response = self.do_request("/ZendServer/Api/configurationExtensionsList")
		return xmltodict.parse(response.text)

	def get_extensions_config(self):
		configuration={'extensions':[]}
		response = self.configuration_extensions_list()
		for extension in response['zendServerAPIResponse']['responseData']['extensions']['extension']:
			configuration['extensions'].append({'name':extension['name'],'value':extension['loaded']})
		return configuration


	def configuration_extensions_on(self,params=[]):
		data = {}
		counter=0
		for param in params:
			data['extensions['+str(counter)+']']=param
			counter = counter+1
		response = self.do_request("/ZendServer/Api/configurationExtensionsOn",data=data)
		return xmltodict.parse(response.text)


	def configuration_extensions_off(self,params=[]):
		data = {}
		counter=0
		for param in params:
			data['extensions['+str(counter)+']']=param
			counter = counter+1
		response = self.do_request("/ZendServer/Api/configurationExtensionsOff",data=data)
		return xmltodict.parse(response.text)

	def synchronize_extensions(self,params):
		require_restart = False
		config_params={}
		for param in params['extensions']:
			config_params[param['name']]=param['value']

		to_enable=[]
		to_disable=[]
		if ('extensions' not in params):
			print ("No extension provided")
		else:
			for param in self.get_extensions_config()['extensions']:
				if param['name'] in config_params:
					if param['value']!=config_params[param['name']]:
						print ("Synchronizing Exenstion "+param['name']+", new: "+config_params[param['name']]+", old: "+param['value'])
						if config_params[param['name']] == 'true':
							to_enable.append(param['name'])
							require_restart=True
						else:
							to_disable.append(param['name'])
							require_restart=True
			if (len(to_enable) > 0):
				self.configuration_extensions_on(to_enable)
			if (len(to_disable) > 0):
				self.configuration_extensions_off(to_disable)

			if (require_restart):
				self.restart_php()

	def configuration_store_directives(self,params=[]):
		data = {}
		for param in params:
			data['directives['+param['name']+']']=param['value']
		response = self.do_request("/ZendServer/Api/configurationStoreDirectives",data=data)
		return xmltodict.parse(response.text)

	def get_directives_config(self):
		configuration={'directives':[]}
		response = self.configuration_directives_list()
		for directive in response['zendServerAPIResponse']['responseData']['directives']['directive']:
			directive_value= (directive['fileValue'] if directive['fileValue'] is not None else directive['defaultValue'])
			configuration['directives'].append({'name':directive['name'],'value':('' if directive_value is None else directive_value)})
		return configuration


	def synchronize_directives(self,params):
		require_restart = False
		config_params={}
		to_edit=[]
		for param in params['directives']:
			config_params[param['name']]=param['value']


		if ('directives' not in params):
			print ("No directives provided")
		else:
			for param in self.get_directives_config()['directives']:
				if param['name'] in config_params:
					if param['value']!=config_params[param['name']]:
						print ("Synchronizing directives "+param['name']+", new: "+config_params[param['name']]+", old: "+param['value'])
						to_edit.append({'name':param['name'],'value':config_params[param['name']]})
						require_restart=True

			if (len(to_edit) > 0):
				self.configuration_store_directives(to_edit)

			if (require_restart):
				self.restart_php()

	def application_update(self,params=[]):
		multipart_data = MultipartEncoder(params)
		response = self.do_request("/ZendServer/Api/applicationUpdate",multipart_data=multipart_data)
		return self.wait_for_deployment(xmltodict.parse(response.text))

	def wait_for_deployment(self,apireturn):
		applicationid = apireturn['zendServerAPIResponse']['responseData']['applicationInfo']['id']
		applicationstatus = apireturn['zendServerAPIResponse']['responseData']['applicationInfo']['status']
		print ("Deployment Status: "+applicationstatus)
		while (applicationstatus != 'deployed'):
			time.sleep(2)
			apireturn = self.application_get_status(applicationid)
			applicationstatus = apireturn['zendServerAPIResponse']['responseData']['applicationsList']['applicationInfo']['status']
			print ("Deployment Status: "+applicationstatus)
		return apireturn

	def deploy_or_update(self,filename,configuration):
		validation_data=self.validate_configuration(filename,configuration)
		if (validation_data['status']):
			print ("Validation sucessfull")
			baseurl=None
			displayname=None
			applicationid=None
			parameters=[]
			for configuration_items in configuration[validation_data['name']]:
				if configuration_items['name'] == 'metadata_displayname':
					displayname=configuration_items['value']
				elif configuration_items['name'] == 'metadata_baseurl':
					baseurl=configuration_items['value']
					url = urllib.parse.urlparse(baseurl)
					if (url.port is None):
						baseurl=url.scheme+'://'+url.hostname+':80'+url.path
				else:
					parameters.append(('userParams['+configuration_items['name']+']',configuration_items['value']))

			for application in self.get_application_list():
				url = urllib.parse.urlparse(application['baseurl'])
				if (url.port is None):
					application['baseurl']=url.scheme+'://'+url.hostname+':80'+url.path
				if (baseurl==application['baseurl']):
					applicationid=application['id']
					displayname=application['displayname']

			parameters.append(('appPackage',(filename, open(filename, 'rb'), 'application/vnd.zend.applicationpackage')))

			print (baseurl)
			print (displayname)

			if (applicationid is None):
				parameters.append(('baseUrl',baseurl))
				parameters.append(('userAppName',displayname))
				parameters.append(('createVhost','true'))
				return self.application_deploy(parameters)
			else:
				parameters.append(('appId',applicationid))
				return self.application_update(parameters)

		return False

	def deploy_or_update_by_id(self,filename,configuration,applicationid):
		print (filename)

		validation_data=self.validate_configuration(filename,configuration)
		if (validation_data['status']):
			print ("Validation sucessfull")
			parameters=[]
			for configuration_items in configuration[validation_data['name']]:
				if configuration_items['name'] == 'metadata_displayname':
					displayname=configuration_items['value']
				elif configuration_items['name'] == 'metadata_baseurl':
					baseurl=configuration_items['value']
					url = urllib.parse.urlparse(baseurl)
					if (url.port is None):
						baseurl=url.scheme+'://'+url.hostname+':80'+url.path
				else:
					parameters.append(('userParams['+configuration_items['name']+']',configuration_items['value']))

			parameters.append(('appPackage',(filename, open(filename, 'rb'), 'application/vnd.zend.applicationpackage')))

			print (baseurl)
			print (displayname)

			if (applicationid is None):
				parameters.append(('baseUrl',baseurl))
				parameters.append(('userAppName',displayname))
				parameters.append(('createVhost','true'))
				return self.application_deploy(parameters)
			else:
				parameters.append(('appId',applicationid))
				return self.application_update(parameters)

		return False

	def validate_configuration(self,filename,configuration):
		archive = zipfile.ZipFile(filename, 'r')
		xmldata = archive.read('deployment.xml')

		package_config=xmltodict.parse(xmldata)
		if package_config['package']['name'] not in configuration:
			return {'status':False,'name':package_config['package']['name']}
		if 'parameters' not in package_config['package']:
			return {'status':True,'name':package_config['package']['name']}
		if package_config['package']['parameters'] is None:
			return {'status':True,'name':package_config['package']['name']}

		is_valid = True
		for parameter in package_config['package']['parameters']['parameter']:
			is_parameter_valid=False
			if parameter['@required'] == 'true':
				for config in configuration[package_config['package']['name']]:
					if config['name'] == parameter['@id'] and config['value'] is not '':
						if 'validation' in parameter:
							if config['value'] in parameter['validation']['enums']['enum']:
								is_parameter_valid=True
						else:
							is_parameter_valid = True
			else:
				is_parameter_valid = True

			if is_parameter_valid == False:
				is_valid=False
		return {'status':is_valid,'name':package_config['package']['name']}

	def tasks_complete(self):
		response = self.do_request("/ZendServer/Api/tasksComplete")
		return xmltodict.parse(response.text)

	def wait_for_task_complete(self):
		while (self.tasks_complete()['zendServerAPIResponse']['responseData']['tasksComplete'] != 'true'):
			print (".", end='', flush=True)
			time.sleep(2)
		print (" complete")

	def restart_daemon(self,param):
		print ("Restarting: "+param, end='', flush=True)
		data={'daemon':param}
		response = self.do_request("/ZendServer/Api/restartDaemon",data=data)
		self.wait_for_task_complete()
		return xmltodict.parse(response.text)

	def cluster_get_server_status(self,server_id=None):
		response = self.do_request("/ZendServer/Api/clusterGetServerStatus"+("?servers[0]="+server_id if server_id is not None else ''))
		return xmltodict.parse(response.text)

	def bootstrap_single_server(self,nodeip,password,order_number,license_key,production=True):
		print ("Bootstrapping server.", end='', flush=True)
		self.__host=nodeip+':10081'
		data={'production':production,
				'adminPassword':password,
				'orderNumber':order_number,
				'licenseKey':license_key,
				'acceptEula':True}
		response = self.do_request("/ZendServer/Api/bootstrapSingleServer",data=data)

		#Setting target automaticaly. Required for the next calls!
		self.__key=xmltodict.parse(response.text)['zendServerAPIResponse']['responseData']['bootstrap']['apiKey']['name']
		self.__hash=xmltodict.parse(response.text)['zendServerAPIResponse']['responseData']['bootstrap']['apiKey']['hash']
		self.wait_for_task_complete()

		#Restarting all the other deamons as they are always in that state post bootstrap.
		self.restart_daemon('jqd')
		self.restart_daemon('scd')
		self.restart_daemon('zdd')
		self.restart_php()

		if (self.cluster_get_server_status()['zendServerAPIResponse']['responseData']['serversList']['serverInfo']['status'] != 'OK'):
			print ("WARNING: SERVER IS NOT IN A CORRECT STATE. DO NOT PERFORM ADD CLUSTER!")
			return None
		return xmltodict.parse(response.text)

	def cluster_add_server(self,servername,nodeip):
		print ("Joining Cluster.", end='', flush=True)
		data={'serverName':servername,
			  'serverIp':nodeip}
		response = self.do_request("/ZendServer/Api/clusterAddServer",data=data)
		server_id = (xmltodict.parse(response.text)['zendServerAPIResponse']['responseData']['serverInfo']['id'])

		self.wait_for_task_complete()
		print ("Restarting and redeploying.", end='', flush=True)
		while (self.cluster_get_server_status(server_id)['zendServerAPIResponse']['responseData']['serversList']['serverInfo']['status'] in  ('restarting','redeploying')):
			print (".", end='', flush=True)
			time.sleep(2)
		if (self.cluster_get_server_status(server_id)['zendServerAPIResponse']['responseData']['serversList']['serverInfo']['status'] != 'OK'):
			print ("WARNING: SERVER IS NOT IN A CORRECT STATE. DO NOT PERFORM ANY OTHER ACTION!")
			return None
		print (" complete")

		restart_required=False
		for servers in self.cluster_get_server_status()['zendServerAPIResponse']['responseData']['serversList']['serverInfo']:
			if servers['status'] != 'OK':
				restart_required=True
		if (restart_required):
			print ("At least one of the server is not in a correct state. Restarting scd/php.")
			self.restart_daemon('scd')
			self.restart_php()
		return xmltodict.parse(response.text)

	def server_add_to_cluster(self,servername,dbhost,dbuser,dbpassword,nodeip,dbname):
		print ("Creating Cluster.", end='', flush=True)
		data={'serverName':servername,
				'dbHost':dbhost,
				'dbUsername':dbuser,
				'dbPassword':dbpassword,
				'nodeIp':nodeip,
				'dbName':dbname}
		response = self.do_request("/ZendServer/Api/serverAddToCluster",data=data)
		self.wait_for_task_complete()
		print ("Restarting and redeploying.", end='', flush=True)
		while (self.cluster_get_server_status()['zendServerAPIResponse']['responseData']['serversList']['serverInfo']['status'] in  ('restarting','redeploying')):
			print (".", end='', flush=True)
			time.sleep(2)
		if (self.cluster_get_server_status()['zendServerAPIResponse']['responseData']['serversList']['serverInfo']['status'] != 'OK'):
			print ("WARNING: SERVER IS NOT IN A CORRECT STATE. DO NOT PERFORM ANY OTHER ACTION!")
			return None
		print (" complete")
		return xmltodict.parse(response.text)

	def get_system_info(self,server_id=None):
		response = self.do_request("/ZendServer/Api/getSystemInfo")
		return xmltodict.parse(response.text)

	def get_server_info(self,server_id=0):
		response = self.do_request("/ZendServer/Api/getServerInfo?serverId="+str(server_id))
		return xmltodict.parse(response.text)
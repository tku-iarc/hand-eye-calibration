#!/usr/bin/env python

import ConfigParser
import rospkg
import numpy as np
import tf
from geometry_msgs.msg import Transform
from visp_hand2eye_calibration.msg import TransformArray
from flexbe_core import EventState
from flexbe_core.proxy import ProxyServiceCaller
from visp_hand2eye_calibration.srv import compute_effector_camera_quick, compute_effector_camera_quickRequest

class ComputeCalibState(EventState):
	"""
	Output a fixed pose to move.

	<= done									   Pose has been published.
	<= fail									   Task fail and finished

	"""
	
	def __init__(self, eye_in_hand_mode, calibration_file_name):
		"""Constructor"""
		super(ComputeCalibState, self).__init__(outcomes=['finish'], input_keys=['base_h_tool', 'camera_h_charuco'])
		self.eye_in_hand_mode = eye_in_hand_mode
		self.calibration_file_name = str(calibration_file_name)
		self.trans_A_list = TransformArray()
		self.trans_B_list = TransformArray()
		self.calib_compute_client = ProxyServiceCaller({'/compute_effector_camera_quick': compute_effector_camera_quick})
    
	def execute(self, userdata):
		req = compute_effector_camera_quickRequest(self.trans_A_list, self.trans_B_list)
		print ("========================================================================================================")
		res = self.calib_compute_client.call('/compute_effector_camera_quick', req)
		
		print('x = '  + str(res.effector_camera.translation.x))
		print('y = '  + str(res.effector_camera.translation.y))
		print('z = '  + str(res.effector_camera.translation.z))
		print('qw = ' + str(res.effector_camera.rotation.w))
		print('qx = ' + str(res.effector_camera.rotation.x))
		print('qy = ' + str(res.effector_camera.rotation.y))
		print('qz = ' + str(res.effector_camera.rotation.z))

		config = ConfigParser.ConfigParser()
		config.optionxform = str #reference: http://docs.python.org/library/configparser.html
		rospack = rospkg.RosPack()
		curr_path = rospack.get_path('charuco_detector')
		config.read(curr_path + '/config/ '+ self.calibration_file_name)
        
		config.add_section("hand_eye_calibration")
		config.set("hand_eye_calibration", "x",  str(res.effector_camera.translation.x))
		config.set("hand_eye_calibration", "y",  str(res.effector_camera.translation.y))
		config.set("hand_eye_calibration", "z",  str(res.effector_camera.translation.z))
		config.set("hand_eye_calibration", "qw", str(res.effector_camera.rotation.w))
		config.set("hand_eye_calibration", "qx", str(res.effector_camera.rotation.x))
		config.set("hand_eye_calibration", "qy", str(res.effector_camera.rotation.y))
		config.set("hand_eye_calibration", "qz", str(res.effector_camera.rotation.z))
		with open(curr_path + '/config/'+ self.calibration_file_name, 'w') as file:
			config.write(file)
		return 'finish'
	
	def on_enter(self, userdata):
		self.trans_A_list = userdata.camera_h_charuco
		if self.eye_in_hand_mode:
			print("------------------------------------------------------------------")
			self.trans_B_list = userdata.base_h_tool
		else:
			self.trans_B_list.header = userdata.base_h_tool.header
			print ("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
			print (userdata.base_h_tool)
			for transform in userdata.base_h_tool.transforms:
				trans = tf.transformations.quaternion_matrix([transform.rotation.x, transform.rotation.y,
															  transform.rotation.z, transform.rotation.w])
				trans[0:3, 3] = [transform.translation.x, transform.translation.y, transform.translation.z]
				trans = tf.transformations.inverse_matrix(trans)
				trans_B = Transform()
				trans_B.translation.x, trans_B.translation.y, trans_B.translation.z = trans[:3, 3]
				trans_B.rotation.x, trans_B.rotation.y, trans_B.rotation.z, \
					trans_B.rotation.w = tf.transformations.quaternion_from_matrix(trans)
				self.trans_B_list.transforms.append(trans_B)

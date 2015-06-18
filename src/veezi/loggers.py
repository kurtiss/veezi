#!/usr/bin/env python
# encoding: utf-8
"""
loggers.py
"""

import os
import json
import logging
import logging.config


def _configure():
	log_cfg = os.getenv("LOG_CFG", 'logging.json')
	if os.path.exists(log_cfg):
		with open(log_cfg, "rt") as f:
			config = json.load(f)
			logging.config.dictConfig(config)
	else:
		logging.basicConfig(level = logging.DEBUG)

_configure()

getLogger = logging.getLogger
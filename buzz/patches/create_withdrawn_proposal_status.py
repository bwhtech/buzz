from buzz.install import create_talk_proposal_statuses


def execute():
	"""Seed the Withdrawn status on sites installed before submitters could withdraw."""
	create_talk_proposal_statuses()

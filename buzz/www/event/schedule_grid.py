from math import ceil, floor

PIXELS_PER_MINUTE = 1.8
COMPACT_HEIGHT = 46
SPEAKER_HEIGHT = 80
MIN_BLOCK_HEIGHT = 16
DEFAULT_START = 9 * 60
DEFAULT_END = 18 * 60


def assign_lanes(blocks: list[dict]) -> None:
	"""Puts overlapping blocks side by side by giving each a `lane` out of `lanes`."""
	cluster: list[dict] = []
	lane_ends: list[int] = []
	for block in sorted(blocks, key=lambda block: block["start"]):
		if cluster and block["start"] >= max(other["end"] for other in cluster):
			set_lane_count(cluster, lane_ends)
			cluster, lane_ends = [], []
		lane = next((index for index, end in enumerate(lane_ends) if end <= block["start"]), len(lane_ends))
		if lane == len(lane_ends):
			lane_ends.append(0)
		lane_ends[lane] = block["end"]
		block["lane"] = lane
		cluster.append(block)
	set_lane_count(cluster, lane_ends)


def set_lane_count(cluster: list[dict], lane_ends: list[int]) -> None:
	for block in cluster:
		block["lanes"] = len(lane_ends)


class ScheduleGrid:
	"""One day as a time grid: a column per track, with each session placed by its time."""

	def __init__(self, rows: list[dict], tracks: list[dict]):
		self.rows = rows
		self.tracks = tracks
		starts = [row["start_minutes"] for row in rows]
		ends = [row["start_minutes"] + row["duration_minutes"] for row in rows]
		self.first = floor(min(starts, default=DEFAULT_START) / 60) * 60
		self.last = ceil(max(ends, default=DEFAULT_END) / 60) * 60

	def as_dict(self) -> dict:
		columns = self.columns()
		return {
			"height": self.pixels(self.last - self.first),
			"hour_height": self.pixels(60),
			"hours": self.hours(),
			"columns": columns or [{"key": "", "title": "", "blocks": []}],
			"has_titles": len(columns) > 1,
			"spans": [self.block(row) for row in self.rows if row["all_rooms"]],
		}

	def columns(self) -> list[dict]:
		columns = []
		for track in self.tracks:
			blocks = [self.block(row) for row in self.rows if row["room_key"] == track.name]
			if blocks:
				assign_lanes(blocks)
				columns.append({"key": track.name, "title": track.title, "blocks": blocks})
		return columns

	def hours(self) -> list[dict]:
		return [
			{"label": f"{minute // 60:02d}:00", "top": self.pixels(minute - self.first)}
			for minute in range(self.first, self.last + 1, 60)
		]

	def block(self, row: dict) -> dict:
		height = max(self.pixels(row["duration_minutes"]) - 2, MIN_BLOCK_HEIGHT)
		return {
			"row": row,
			"start": row["start_minutes"],
			"end": row["start_minutes"] + row["duration_minutes"],
			"top": self.pixels(row["start_minutes"] - self.first) + 1,
			"height": height,
			"is_compact": height < COMPACT_HEIGHT,
			"shows_speakers": height >= SPEAKER_HEIGHT and bool(row["people"]),
			"lane": 0,
			"lanes": 1,
		}

	@staticmethod
	def pixels(minutes: int) -> int:
		return round(minutes * PIXELS_PER_MINUTE)

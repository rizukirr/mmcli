video_formats = [
    {"alias": "mp4", "format": "mp4", "desc": "MPEG-4 Part 14"},
    {"alias": "mkv", "format": "matroska", "desc": "Matroska Multimedia Container"},
    {"alias": "avi", "format": "avi", "desc": "Audio Video Interleaved"},
    {"alias": "mov", "format": "mov", "desc": "QuickTime Movie"},
    {"alias": "flv", "format": "flv", "desc": "Flash Video"},
    {"alias": "webm", "format": "webm", "desc": "WebM Video"},
    {"alias": "mpeg", "format": "mpeg", "desc": "MPEG Program Stream"},
    {"alias": "mpg", "format": "mpeg", "desc": "MPEG Program Stream"},
    {"alias": "ts", "format": "mpegts", "desc": "MPEG Transport Stream"},
    {"alias": "m2ts", "format": "mpegts", "desc": "MPEG-2 Transport Stream"},
    {"alias": "ogv", "format": "ogg", "desc": "Ogg Video"},
    {"alias": "3gp", "format": "3gp", "desc": "3GPP Multimedia Container"},
    {"alias": "3g2", "format": "3g2", "desc": "3GPP2 Multimedia Container"},
    {"alias": "vob", "format": "vob", "desc": "DVD Video Object"},
    {"alias": "f4v", "format": "f4v", "desc": "Flash Video F4V"},
    {"alias": "wmv", "format": "asf", "desc": "Windows Media Video"},
    {"alias": "rm", "format": "rm", "desc": "RealMedia"},
    {"alias": "rmvb", "format": "rm", "desc": "RealMedia Variable Bitrate"},
]

audio_formats = [
    {"alias": "mp3", "format": "mp3", "desc": "MPEG Audio Layer III"},
    {"alias": "wav", "format": "wav", "desc": "Waveform Audio File Format"},
    {"alias": "flac", "format": "flac", "desc": "Free Lossless Audio Codec"},
    {"alias": "aac", "format": "aac", "desc": "Advanced Audio Coding"},
    {"alias": "m4a", "format": "ipod", "desc": "MPEG-4 Audio"},
    {"alias": "ogg", "format": "ogg", "desc": "Ogg Vorbis/Opus"},
    {"alias": "oga", "format": "ogg", "desc": "Ogg Audio"},
    {"alias": "opus", "format": "ogg", "desc": "Opus in Ogg"},
    {"alias": "wma", "format": "asf", "desc": "Windows Media Audio"},
    {"alias": "alac", "format": "ipod", "desc": "Apple Lossless Audio Codec"},
    {"alias": "amr", "format": "amr", "desc": "Adaptive Multi-Rate Audio"},
    {"alias": "ac3", "format": "ac3", "desc": "Dolby Digital AC-3"},
    {"alias": "dts", "format": "dts", "desc": "Digital Theater Systems"},
    {"alias": "eac3", "format": "eac3", "desc": "Enhanced AC-3"},
]

all_formats = video_formats + audio_formats


def get_format(format: str, formats: list = all_formats) -> list:
    return list(
        filter(lambda f: f["alias"] == format or f["format"] == format, formats)
    )


def is_audio_format(alias: str) -> bool:
    """True when alias names an audio output format."""
    return any(f["alias"] == alias for f in audio_formats)


def is_video_format(alias: str) -> bool:
    """True when alias names a video output format."""
    return any(f["alias"] == alias for f in video_formats)

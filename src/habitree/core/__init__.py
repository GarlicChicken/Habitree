"""코어: 모든 명령이 함께 쓰는 입출력·경로·설정·규칙 DB. / Core shared by every command."""


class HabitreeError(Exception):
    """사용자에게 그대로 보여 줄 오류. / An error shown to the user as is."""

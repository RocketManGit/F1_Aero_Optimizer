import fastf1

fastf1.Cache.enable_cache("cache/")

session = fastf1.get_session(2023, "Italian", "Q")
session.load(telemetry=True, weather=False, messages=False)

fastest = session.laps.pick_fastest()
tel = fastest.get_telemetry()

print(tel[["X", "Y", "Z"]].head(10))
print(f"\nTotal telemetry points: {len(tel)}")
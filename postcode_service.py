import json
from pathlib import Path
from typing import Any

class PostcodeService:
    """
    Loads Malaysia postcode data from a folder that may contain:
    - all.json style: {"state":[{"name": "...", "city":[{"name":"...", "postcode":[...]}]}]}
      (matches your all.json structure) :contentReference[oaicite:2]{index=2}
    - per-state style: {"name":"Johor","city":[{"name":"...","postcode":[...]}]}
      (matches johor.json, kedah.json etc.) 
    """

    def __init__(self, data_path: str | Path):
        self.data_path = Path(data_path)

        # Indexes for instant UI response
        self.postcode_index: dict[str, dict[str, str]] = {}
        self.city_index: dict[str, dict[str, Any]] = {}

        states = self._load_all_states(self.data_path)
        self._build_indexes(states)

    # ---------------------------
    # Loading + Normalization
    # ---------------------------
    def _load_all_states(self, p: Path) -> list[dict[str, Any]]:
        if p.is_file():
            return self._normalize_to_states(self._read_json(p), source_name=p.name)

        if not p.exists():
            raise FileNotFoundError(f"Data path not found: {p}")

        all_states: list[dict[str, Any]] = []
        json_files = sorted([x for x in p.glob("*.json") if x.is_file()])

        if not json_files:
            raise FileNotFoundError(f"No .json files found in: {p}")

        for jf in json_files:
            data = self._read_json(jf)
            states = self._normalize_to_states(data, source_name=jf.name)
            all_states.extend(states)

        # De-duplicate by state name (keep the one with more cities if duplicated)
        merged: dict[str, dict[str, Any]] = {}
        for st in all_states:
            key = (st.get("name") or "").strip().lower()
            if not key:
                continue
            if key not in merged:
                merged[key] = st
            else:
                # pick whichever has more cities
                if len(st.get("cities", [])) > len(merged[key].get("cities", [])):
                    merged[key] = st

        return list(merged.values())

    def _read_json(self, path: Path) -> dict[str, Any]:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _normalize_to_states(self, data: Any, source_name: str) -> list[dict[str, Any]]:
        """
        Output format:
        [
          {"name": "Johor", "code": "JHR" or "", "cities":[{"name":"Johor Bahru","postcodes":[...]}, ...]},
          ...
        ]
        """
        if not isinstance(data, dict):
            return []

        # Format A: all.json style (your snippet shows "state" -> list, "city" -> list, "postcode" -> list) :contentReference[oaicite:4]{index=4}
        if "state" in data and isinstance(data["state"], list):
            out = []
            for st in data["state"]:
                st_name = (st.get("name") or "").strip()
                cities_raw = st.get("city") or []
                cities = []
                for c in cities_raw:
                    cities.append({
                        "name": (c.get("name") or "").strip(),
                        "postcodes": [str(x).strip() for x in (c.get("postcode") or [])]
                    })
                out.append({"name": st_name, "code": st.get("code", "") or "", "cities": cities})
            return out

        # Format B: per-state file style: {"name":"Johor","city":[{"name":"Ayer Baloi","postcode":[...]}]} 
        if "name" in data and "city" in data and isinstance(data["city"], list):
            st_name = (data.get("name") or "").strip()
            cities = []
            for c in data["city"]:
                cities.append({
                    "name": (c.get("name") or "").strip(),
                    "postcodes": [str(x).strip() for x in (c.get("postcode") or [])]
                })
            return [{"name": st_name, "code": data.get("code", "") or "", "cities": cities}]

        # Format C: already in "states" / "cities" / "postcodes" (some repos use this)
        if "states" in data and isinstance(data["states"], list):
            out = []
            for st in data["states"]:
                st_name = (st.get("name") or "").strip()
                st_code = st.get("code", "") or ""
                cities = []
                for c in (st.get("cities") or []):
                    cities.append({
                        "name": (c.get("name") or "").strip(),
                        "postcodes": [str(x).strip() for x in (c.get("postcodes") or [])]
                    })
                out.append({"name": st_name, "code": st_code, "cities": cities})
            return out

        return []

    # ---------------------------
    # Indexing
    # ---------------------------
    def _build_indexes(self, states: list[dict[str, Any]]):
        for st in states:
            state_name = st.get("name", "")
            state_code = st.get("code", "") or ""
            for city in st.get("cities", []):
                city_name = city.get("name", "")
                postcodes = city.get("postcodes", []) or []

                # City index
                city_key = city_name.strip().lower()
                if city_key:
                    self.city_index[city_key] = {
                        "city": city_name,
                        "state": state_name,
                        "state_code": state_code,
                        "postcodes": postcodes
                    }

                # Postcode index
                for pc in postcodes:
                    pc_str = str(pc).strip()
                    if pc_str:
                        self.postcode_index[pc_str] = {
                            "postcode": pc_str,
                            "city": city_name,
                            "state": state_name,
                            "state_code": state_code
                        }

    # ---------------------------
    # Public API used by GUI/API
    # ---------------------------
    def validate_postcode(self, postcode: str) -> dict:
        pc = str(postcode).strip()
        if pc in self.postcode_index:
            return {"valid": True, **self.postcode_index[pc]}
        return {"valid": False, "postcode": pc}

    def lookup_by_postcode(self, postcode: str) -> dict | None:
        return self.postcode_index.get(str(postcode).strip())

    def lookup_by_city(self, city: str) -> dict | None:
        return self.city_index.get(str(city).strip().lower())

    def search_cities(self, query: str, limit: int = 80) -> list[str]:
        q = str(query).strip().lower()
        if not q:
            return []
        out = []
        for k, v in self.city_index.items():
            if q in k:
                out.append(v["city"])
                if len(out) >= limit:
                    break
        return out

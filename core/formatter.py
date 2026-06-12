import json
from core import tl
from core import kick
from core import view_controller
from core import events

# Обновленная версия sync_drops_data с campaign_id
def sync_drops_data(server_data, cookies, filepath="current_views.json"):
    try:
        # Load local JSON
        events.emit(events.EventType.INFO, f"Loading local JSON from {filepath}...")
        with open(filepath, 'r', encoding='utf-8') as f:
            local_data = json.load(f)
        
        # Create a copy of local data
        updated_data = json.loads(json.dumps(local_data))
        
        # Dictionary for quick reward lookup
        server_rewards_map = {}
        # Per-campaign cumulative watched-minutes counter (server truth).
        server_progress_units = {}

        # Collect all rewards from all server campaigns
        if 'data' in server_data and isinstance(server_data['data'], list):

            for idx, campaign in enumerate(server_data['data']):
                # Пропускаем кампании со статусом "expired"
                status = campaign.get('status')
                if status == 'expired':
                    events.emit(events.EventType.INFO, f"Skipping expired campaign: {campaign.get('name', 'Unnamed')}")
                    continue

                campaign_id = campaign.get('id')
                server_progress_units[campaign_id] = campaign.get('progress_units', 0)
                events.emit(events.EventType.INFO, f"Processing campaign: {campaign.get('name', 'Unnamed')}")
                
                if 'rewards' in campaign and isinstance(campaign['rewards'], list):
                    events.emit(events.EventType.INFO, f"Rewards found: {len(campaign['rewards'])}")
                    
                    for reward in campaign['rewards']:
                        reward_id = reward.get('id')
                        progress = reward.get('progress')
                        claimed = reward.get('claimed')
                        
                        if progress == 1 and claimed is False:
                            events.emit(events.EventType.DROP_STATUS, f"Found unclaimed reward: {reward.get('name')}")
                            
                            # Клеймим награду
                            config_status = view_controller.checkautoclaim_config()
                            if config_status == True:
                                claim_result = kick.claim_drop_reward(reward_id, campaign_id, cookies)
                                
                                if claim_result and claim_result.get('message') == 'Success':
                                    # Добавляем в map как заклейменную
                                    server_rewards_map[reward_id] = {
                                        'claimed': True,
                                        'progress': 1,
                                        'external_id': reward.get('external_id'),
                                        'name': reward.get('name')
                                    }
                                    events.emit(events.EventType.SUCCESS, f"Claimed: {reward.get('name')}")
                                else:
                                    events.emit(events.EventType.ERROR, f"Failed to claim: {reward.get('name')}")

                        elif claimed is True and progress == 1:
                            server_rewards_map[reward_id] = {
                                'claimed': claimed,
                                'progress': progress,
                                'external_id': reward.get('external_id'),
                                'name': reward.get('name')
                            }
                            events.emit(events.EventType.DROP_STATUS, f"Already claimed: {reward.get('name')}")

        updated_count = 0
        if 'data' in updated_data and 'planned' in updated_data['data']:
            for item in updated_data['data']['planned']:
                item_id = item.get('id')
                if item_id in server_rewards_map:
                    if item.get('claim') != 1:
                        item['claim'] = 1
                        updated_count += 1
                        events.emit(events.EventType.DROP_STATUS, f"Updated drop ID: {item_id}")
                # Overlay the campaign's cumulative watch counter (server truth)
                # onto every reward-item belonging to that campaign.
                cid = item.get('campaign_id')
                if cid in server_progress_units:
                    item['progress_units'] = server_progress_units[cid]

        events.emit(events.EventType.SUCCESS, f"Total updated: {updated_count} drops")

        events.emit(events.EventType.INFO, f"Saving data to {filepath}...")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(updated_data, f, ensure_ascii=False, indent=4)

        events.emit(events.EventType.SUCCESS, f"Data saved to {filepath}")
        return True

    except FileNotFoundError:
        events.emit(events.EventType.ERROR, f"File not found: {filepath}")
        return False
    except json.JSONDecodeError as e:
        events.emit(events.EventType.ERROR, f"JSON read error: {e}")
        return False
    except Exception as e:
        events.emit(events.EventType.ERROR, f"Synchronization error: {e}")
        return False


def convert_drops_json(drops_data, out_path='current_views.json'):
    """Build current_views.json from the /drops/campaigns response.

    Schema: ONE planned item per reward (a campaign with tiered rewards yields
    several items that share a ``campaign_id``).  ``required_units`` is the
    reward's tier and never changes; ``progress_units`` is the campaign's
    cumulative watched-minutes counter, overlaid from /drops/progress on sync.
    Watch-time for a campaign is therefore ``max(unclaimed tier) - progress_units``
    -- tiers share one counter, they are not additive.
    """
    result = {
        "data": {
            "planned": [],
            "finished": []
        }
    }

    if 'data' not in drops_data:
        return result

    for campaign in drops_data['data']:
        # Пропускаем кампании со статусом "expired"
        status = campaign.get('status')
        if status == 'expired':
            continue

        category_id = campaign.get('category', {}).get('id')

        if category_id is None:
            continue

        campaign_id = campaign.get('id')
        channels = campaign.get('channels', [])
        rewards = campaign.get('rewards', [])

        # type 2 (general) when there are no channels, else type 1 (streamer).
        is_general = not channels
        usernames = []
        if not is_general:
            for channel in channels:
                slug = channel.get('slug')
                if slug:
                    usernames.append(slug)

        # One item per reward for BOTH types -- tiers tracked individually,
        # never summed.  Items in the same campaign share campaign_id and (for
        # streamer campaigns) the same usernames.
        for reward in rewards:
            required_units = reward.get('required_units', 0)
            planned_item = {
                "category_id": category_id,
                "campaign_id": campaign_id,
                "type": 2 if is_general else 1,
                "claim": 0,
                "required_units": required_units,
                "total_units": required_units,  # original tier, for progress %
                "progress_units": 0,            # cumulative watched minutes (from server)
                "id": reward.get('id'),
            }
            if not is_general:
                planned_item["usernames"] = usernames
            result['data']['planned'].append(planned_item)

    # Сохраняем результат
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=4)

    return result


# -- Campaign-aware aggregation helpers -----------------------------------

def _campaign_groups(planned):
    """Group planned reward-items by campaign_id (preserving order)."""
    groups = {}
    for item in planned:
        cid = item.get('campaign_id') or item.get('id')
        groups.setdefault(cid, []).append(item)
    return groups


def campaign_remaining_minutes(items):
    """Remaining watch-minutes for one campaign's reward-items.

    A campaign's watch counter is shared across its tiers, so the time left is
    the highest *unclaimed* tier minus the cumulative ``progress_units``,
    floored at zero.  When every reward is claimed, nothing remains.
    """
    unclaimed_tiers = [
        float(i.get('required_units', 0) or 0)
        for i in items
        if i.get('claim') != 1
    ]
    if not unclaimed_tiers:
        return 0.0
    progress = float(items[0].get('progress_units', 0) or 0)
    return max(0.0, max(unclaimed_tiers) - progress)


def aggregate_remaining(planned):
    """Return (streamer_remaining, general_remaining) in minutes.

    Streamer campaigns must each be watched in turn, so their remaining times
    add up.  General drops fill concurrently from any watching, so the overall
    time-to-finish is ``max(streamer_total, general_total)`` -- computed by the
    caller, not here.
    """
    streamer_total = 0.0
    general_total = 0.0
    for items in _campaign_groups(planned).values():
        remaining = campaign_remaining_minutes(items)
        if items[0].get('type') == 2:
            general_total += remaining
        else:
            streamer_total += remaining
    return streamer_total, general_total


def collect_usernames(json_filename='current_views.json'):
    """One entry per streamer username with the campaign's remaining watch time.

    Remaining is ``max(unclaimed tier) - progress_units`` for the streamer's
    campaign, so a multi-tier campaign (e.g. kick 120/60) reports the single
    watch needed, not the sum.
    """
    with open(json_filename, 'r', encoding='utf-8') as f:
        data = json.load(f)

    planned = data['data']['planned']
    streamers_data = []
    for items in _campaign_groups(planned).values():
        if items[0].get('type') != 1:
            continue
        remaining_minutes = campaign_remaining_minutes(items)
        # Campaign is "claimed" only when every reward in it is claimed.
        claim_status = 1 if all(i.get('claim') == 1 for i in items) else 0
        for username in items[0].get('usernames', []):
            streamers_data.append({
                'username': username,
                'required_seconds': int(remaining_minutes * 60),
                'claim': claim_status
            })

    return streamers_data

def update_streamer_progress(username: str, watched_seconds: int, json_filename='current_views.json', update_type: int = 1):
    """Advance the cumulative watch counter for live (between-sync) feedback.

    Watching advances the streamer's own campaign **and** every general
    campaign 1:1 -- a relationship confirmed against the server (the sum of
    streamer ``progress_units`` equals the general counter).  ``progress_units``
    is transient: the next server sync overwrites it with ground truth.
    """
    watched_minutes = round(watched_seconds / 60.0, 1)

    try:
        with open(json_filename, 'r', encoding='utf-8') as f:
            data = json.load(f)

        planned = data['data']['planned']

        # Which campaigns does this watching advance?  The streamer's own
        # campaign(s), plus all general campaigns (any Rust watching counts).
        bump_ids = set()
        for item in planned:
            if item.get('type') == 1 and username in (item.get('usernames') or []):
                bump_ids.add(item.get('campaign_id'))
            if item.get('type') == 2:
                bump_ids.add(item.get('campaign_id'))

        if not bump_ids:
            events.emit(events.EventType.WARNING, tl.c["streamer_notfound_in_json_updating"].format(username=username))
            return False

        before = after = 0.0
        for item in planned:
            if item.get('campaign_id') in bump_ids:
                current = round(float(item.get('progress_units', 0) or 0), 1)
                updated = round(current + watched_minutes, 1)
                item['progress_units'] = updated
                # Report using the streamer's own campaign for the event message.
                if item.get('type') == 1 and username in (item.get('usernames') or []):
                    before, after = current, updated

        events.emit(events.EventType.PROGRESS, tl.c["user_progress"].format(
            username=username,
            current_units=before,
            new_units=after,
            watched_minutes=watched_minutes
        ), data={"type": "streamer", "username": username, "progress_units": after})

        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        return True

    except Exception as e:
        events.emit(events.EventType.ERROR, tl.c["error_updating_progress"].format(e=e))
        return False

async def get_remaining_time(username: str = None, json_filename='current_views.json', get_type: int = 1) -> int:
    """Remaining watch-seconds for a streamer's campaign (type 1) or general (type 2).

    Computed as ``max(unclaimed tier) - progress_units`` for the campaign.
    """
    try:
        with open(json_filename, 'r', encoding='utf-8') as f:
            data = json.load(f)

        planned = data['data']['planned']

        for items in _campaign_groups(planned).values():
            head = items[0]
            if get_type == 2 and head.get('type') == 2:
                return int(campaign_remaining_minutes(items) * 60)
            elif (
                get_type == 1
                and head.get('type') == 1
                and username in (head.get('usernames') or [])
            ):
                return int(campaign_remaining_minutes(items) * 60)

        if get_type == 1:
            events.emit(events.EventType.WARNING, tl.c["streamer_notfound_in_json_get"].format(username=username))
            return await get_remaining_time(username, json_filename, get_type=2)
        else:
            events.emit(events.EventType.ERROR, tl.c["general_type_2_notfound_in_json"])
            return 0

    except Exception as e:
        events.emit(events.EventType.ERROR, tl.c["error_getting_progress"].format(e=e))
        return 0
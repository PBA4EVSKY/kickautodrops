import json
from core import tl
from core import kick
import json

# Обновленная версия sync_drops_data с campaign_id
def sync_drops_data(server_data, cookies, filepath="current_views.json"):
    try:
        # Load local JSON
        print(f"Loading local JSON from {filepath}...")
        with open(filepath, 'r', encoding='utf-8') as f:
            local_data = json.load(f)
        
        # Create a copy of local data
        updated_data = json.loads(json.dumps(local_data))
        
        # Dictionary for quick reward lookup
        server_rewards_map = {}
        
        # Collect all rewards from all server campaigns
        if 'data' in server_data and isinstance(server_data['data'], list):
            
            for idx, campaign in enumerate(server_data['data']):
                campaign_id = campaign.get('id')
                print(f"  Processing campaign {idx}: {campaign.get('name', 'Unnamed')} (ID: {campaign_id})")
                
                if 'rewards' in campaign and isinstance(campaign['rewards'], list):
                    print(f"    Rewards found: {len(campaign['rewards'])}")
                    
                    for reward in campaign['rewards']:
                        reward_id = reward.get('id')
                        progress = reward.get('progress')
                        claimed = reward.get('claimed')
                        
                        # Если progress == 1 и claimed == False - нужно заклеймить
                        if progress == 1 and claimed is False:
                            print(f"⚠ Found unclaimed reward: {reward.get('name')} (ID: {reward_id})")
                            
                            # Клеймим награду
                            claim_result = kick.claim_drop_reward(reward_id, campaign_id, cookies)
                            
                            if claim_result and claim_result.get('message') == 'Success':
                                # Добавляем в map как заклейменную
                                server_rewards_map[reward_id] = {
                                    'claimed': True,
                                    'progress': 1,
                                    'external_id': reward.get('external_id'),
                                    'name': reward.get('name')
                                }
                                print(f"✓ Successfully claimed and added: {reward.get('name')}")
                            else:
                                print(f"✗ Failed to claim: {reward.get('name')}")
                        
                        # Если уже claimed = True и progress = 1 - просто обновляем локальный JSON
                        elif claimed is True and progress == 1:
                            server_rewards_map[reward_id] = {
                                'claimed': claimed,
                                'progress': progress,
                                'external_id': reward.get('external_id'),
                                'name': reward.get('name')
                            }
                            print(f"✓ Added claimed reward: {reward.get('name')} (ID: {reward_id})")
        
        # Update local data
        updated_count = 0
        if 'data' in updated_data and 'planned' in updated_data['data']:
            for item in updated_data['data']['planned']:
                item_id = item.get('id')
                if item_id in server_rewards_map:
                    if item.get('claim') != 1:
                        item['claim'] = 1
                        updated_count += 1
                        print(f"✓ Updated drop ID: {item_id} (claim: 0 → 1)")
        
        print(f"\nTotal updated: {updated_count} drops")
        
        # Save updated data
        print(f"Saving data to {filepath}...")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(updated_data, f, ensure_ascii=False, indent=4)
        
        print(f"✓ Data successfully saved to {filepath}")
        return True
        
    except FileNotFoundError:
        print(f"✗ Error: file {filepath} not found")
        return False
    except json.JSONDecodeError as e:
        print(f"✗ JSON read error: {e}")
        return False
    except Exception as e:
        print(f"✗ Synchronization error: {e}")
        return False


def convert_drops_json(drops_data):
    result = {
        "data": {
            "planned": [],
            "finished": []
        }
    }
    
    if 'data' not in drops_data:
        return result
    
    for campaign in drops_data['data']:
        category_id = campaign.get('category', {}).get('id')
        
        if category_id is None:
            continue
        
        
        # Проверяем наличие channels
        channels = campaign.get('channels', [])
        
        # Если channels пустой - это type 2 (создаем запись для каждой награды)
        if not channels or len(channels) == 0:
            rewards = campaign.get('rewards', [])
            
            for reward in rewards:
                reward_id = reward.get('id')
                required_units = reward.get('required_units', 0)
                
                planned_item = {
                    "category_id": category_id,
                    "type": 2,
                    "claim": 0,
                    "required_units": required_units,
                    "id": reward_id  # ID конкретной награды
                }
                result['data']['planned'].append(planned_item)
        
        # Если channels не пустой - это type 1 (одна запись на всю кампанию)
        else:
            usernames = []
            for channel in channels:
                slug = channel.get('slug')
                if slug:
                    usernames.append(slug)
            
            # Считаем общее количество required_units из всех rewards
            total_required_units = 0
            rewards = campaign.get('rewards', [])
            
            for reward in rewards:
                required_units = reward.get('required_units', 0)
                total_required_units += required_units
                reward_id = reward.get('id')
            planned_item = {
                "category_id": category_id,
                "type": 1,
                "claim": 0,
                "usernames": usernames,
                "required_units": total_required_units,
                "id": reward_id  # ID кампании
            }
            result['data']['planned'].append(planned_item)
    
    # Сохраняем результат
    with open('current_views.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=4)
    
    return result


def collect_usernames(json_filename='current_views.json'):
    with open(json_filename, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    streamers_data = []
    for item in data['data']['planned']:
        if 'usernames' in item:
            required_minutes = item.get('required_units', 0)
            claim_status = item.get('claim')
            for username in item['usernames']:
                streamers_data.append({
                    'username': username,
                    'required_seconds': required_minutes * 60,
                    'claim': claim_status
                })
    
    return streamers_data

def update_streamer_progress(username: str, watched_seconds: int, json_filename='current_views.json', update_type: int = 1):
    # Конвертируем секунды в минуты
    watched_minutes = round(watched_seconds / 60.0, 1)
    
    try:
        # Читаем JSON
        with open(json_filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Проходим по всем planned элементам
        for item in data['data']['planned']:
            # Обновление для general (type=2)
            if update_type == 2 and item.get('type') == 2:
                current_units = round(float(item.get('required_units', 0)), 1)
                new_units = round(max(0.0, current_units - watched_minutes), 1)
                
                item['required_units'] = new_units
                
                print(tl.c["general_progress"].format(
                    current_units=current_units,
                    new_units=new_units,
                    watched_minutes=watched_minutes
                ))
                
                with open(json_filename, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
                
                return True
            
            # Обновление для конкретного стримера (type=1)
            elif update_type == 1 and item.get('type') == 1 and 'usernames' in item and username in item['usernames']:
                current_units = round(float(item.get('required_units', 0)), 1)
                new_units = round(max(0.0, current_units - watched_minutes), 1)
                
                item['required_units'] = new_units
                
                print(tl.c["user_progress"].format(
                    username=username,
                    current_units=current_units,
                    new_units=new_units,
                    watched_minutes=watched_minutes
                ))
                
                with open(json_filename, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
                
                return True
        
        # Если стример не найден (type=1), пытаемся обновить general (type=2)
        if update_type == 1:
            print(f"{tl.c['streamer_notfound_in_json_updating'].format(username=username)}")
            return update_streamer_progress(username, watched_seconds, json_filename, update_type=2)
        else:
            print(f"{tl.c['general_type_2_notfound_in_json']}")
            return False
        
    except Exception as e:
        print(f"{tl.c['error_updating_progress'].format(e=e)}")
        return False
    
async def get_remaining_time(username: str = None, json_filename='current_views.json', get_type: int = 1) -> int:
    try:
        with open(json_filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for item in data['data']['planned']:
            # Получение для general (type=2)
            if get_type == 2 and item.get('type') == 2:
                remaining_minutes = item.get('required_units', 0)
                return int(remaining_minutes * 60)
            
            # Получение для конкретного стримера (type=1)
            elif get_type == 1 and item.get('type') == 1 and 'usernames' in item and username in item['usernames']:
                remaining_minutes = item.get('required_units', 0)
                return int(remaining_minutes * 60)
        
        # Если стример не найден (type=1), получаем время из general (type=2)
        if get_type == 1:
            print(f"{tl.c['streamer_notfound_in_json_get'].format(username=username)}")
            # Await the recursive async call so we return an int, not a coroutine
            return await get_remaining_time(username, json_filename, get_type=2)
        else:
            print(f"{tl.c['general_type_2_notfound_in_json']}")
            return 0
        
    except Exception as e:
        print(f"{tl.c['error_getting_progress'].format(e=e)}")
        return 0
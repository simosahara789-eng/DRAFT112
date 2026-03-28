import streamlit as st
import requests
import json
import time

# Page configuration
st.set_page_config(page_title="Reverb Draft Manager", page_icon="📋", layout="centered")
st.title("📋 Reverb Draft Manager - Fixed Version")
st.markdown("---")

API_BASE = "https://api.reverb.com/api"

def get_my_drafts(api_key):
    """Fetch all drafts from my account"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept-Version": "3.0",
        "Content-Type": "application/json"
    }
    
    try:
        # Get my listings (drafts) - CORRECT ENDPOINT
        response = requests.get(
            f"{API_BASE}/my/listings",
            headers=headers,
            params={"state": "draft", "per_page": 50},
            timeout=15
        )
        
        if response.status_code != 200:
            return None, f"Error fetching drafts: {response.status_code}"
        
        data = response.json()
        
        # Extract listings from response
        if "listings" in data:
            return data["listings"], None
        elif isinstance(data, list):
            return data, None
        else:
            return [], None
            
    except Exception as e:
        return None, str(e)

def publish_draft(api_key, listing_id):
    """Publish a draft listing - CORRECTED ENDPOINT"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept-Version": "3.0",
        "Content-Type": "application/json"
    }
    
    # Try different possible publish endpoints
    endpoints_to_try = [
        f"{API_BASE}/listings/{listing_id}/publish",
        f"{API_BASE}/my/listings/{listing_id}/publish",
        f"{API_BASE}/listings/{listing_id}/state/publish",
        f"{API_BASE}/my/listings/{listing_id}/state/publish"
    ]
    
    for endpoint in endpoints_to_try:
        try:
            st.write(f"Trying: {endpoint}")
            response = requests.put(
                endpoint,
                headers=headers,
                timeout=15
            )
            
            if response.status_code in [200, 201, 204]:
                return True, f"✅ Published successfully!"
            elif response.status_code == 404:
                continue  # Try next endpoint
            else:
                return False, f"Error: {response.status_code} - {response.text[:100]}"
                
        except Exception as e:
            continue
    
    return False, "❌ Could not publish - all endpoints failed"

def delete_draft(api_key, listing_id):
    """Delete a draft listing"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept-Version": "3.0",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.delete(
            f"{API_BASE}/listings/{listing_id}",
            headers=headers,
            timeout=15
        )
        
        if response.status_code in [200, 201, 204]:
            return True, "✅ Deleted successfully!"
        else:
            return False, f"Error: {response.status_code}"
            
    except Exception as e:
        return False, str(e)

def check_listing_details(api_key, listing_id):
    """Get detailed information about a listing"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept-Version": "3.0"
    }
    
    try:
        response = requests.get(
            f"{API_BASE}/listings/{listing_id}",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json(), None
        else:
            return None, f"Error: {response.status_code}"
            
    except Exception as e:
        return None, str(e)

# Main interface
st.header("🔑 Connect to Reverb")

# API Key input
api_key = st.text_input("Enter your Reverb API Key", type="password", help="Your API key must have write permissions")

if api_key:
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📋 Load My Drafts", type="primary", use_container_width=True):
            with st.spinner("Loading your drafts..."):
                drafts, error = get_my_drafts(api_key)
                
                if error:
                    st.error(f"❌ {error}")
                elif drafts:
                    st.success(f"✅ Found {len(drafts)} drafts in your account")
                    st.session_state.drafts = drafts
                else:
                    st.info("No drafts found in your account")
    
    with col2:
        if st.button("🔄 Refresh", use_container_width=True):
            if 'drafts' in st.session_state:
                del st.session_state.drafts
                st.rerun()
    
    # Display drafts if they exist in session state
    if 'drafts' in st.session_state and st.session_state.drafts:
        st.markdown("---")
        st.header(f"📋 Your Drafts ({len(st.session_state.drafts)})")
        
        for idx, draft in enumerate(st.session_state.drafts):
            # Extract listing info
            listing_id = draft.get('id')
            title = draft.get('title', 'Untitled')
            make = draft.get('make', 'Unknown')
            model = draft.get('model', 'Unknown')
            
            # Handle price safely
            price_data = draft.get('price', {})
            if isinstance(price_data, dict):
                price = price_data.get('amount', '0')
                currency = price_data.get('currency', 'USD')
            else:
                price = str(price_data)
                currency = 'USD'
            
            # Get photos
            photos = draft.get('photos', [])
            photo_count = len(photos)
            
            # Get state
            state_data = draft.get('state', {})
            if isinstance(state_data, dict):
                state = state_data.get('slug', 'unknown')
            else:
                state = str(state_data)
            
            # Display each draft in a card
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                
                with col1:
                    st.write(f"**{title}**")
                    st.write(f"📌 ID: `{listing_id}`")
                    st.write(f"🏷️ {make} - {model}")
                    st.write(f"💰 {price} {currency}")
                    st.write(f"🖼️ {photo_count} photos")
                    st.write(f"📌 Status: {state}")
                
                with col2:
                    # Check details button
                    if st.button(f"🔍 Details", key=f"det_{listing_id}_{idx}"):
                        with st.spinner("Checking..."):
                            details, error = check_listing_details(api_key, listing_id)
                            if details:
                                st.info(f"Full status: {details.get('state', {}).get('description', 'Unknown')}")
                            else:
                                st.error(f"Error: {error}")
                
                with col3:
                    # Publish button
                    if st.button(f"🚀 Publish", key=f"pub_{listing_id}_{idx}"):
                        with st.spinner("Publishing..."):
                            success, message = publish_draft(api_key, listing_id)
                            if success:
                                st.success(message)
                                # Wait a bit then refresh
                                time.sleep(2)
                                # Refresh drafts
                                drafts, error = get_my_drafts(api_key)
                                if not error:
                                    st.session_state.drafts = drafts
                                    st.rerun()
                            else:
                                st.error(message)
                                
                                # Try to get more info
                                details, det_error = check_listing_details(api_key, listing_id)
                                if details:
                                    st.info(f"Listing status: {details.get('state', {}).get('description', 'Unknown')}")
                                    st.info(f"Missing required fields: {details.get('errors', 'None')}")
                
                with col4:
                    # Delete button
                    if st.button(f"🗑️ Delete", key=f"del_{listing_id}_{idx}"):
                        with st.spinner("Deleting..."):
                            success, message = delete_draft(api_key, listing_id)
                            if success:
                                st.success(message)
                                time.sleep(1)
                                # Refresh drafts
                                drafts, error = get_my_drafts(api_key)
                                if not error:
                                    st.session_state.drafts = drafts
                                    st.rerun()
                            else:
                                st.error(message)
                
                # Show first photo if available
                if photos and len(photos) > 0:
                    try:
                        first_photo = photos[0]
                        if isinstance(first_photo, dict):
                            if '_links' in first_photo and 'small' in first_photo['_links']:
                                img_url = first_photo['_links']['small']['href']
                                st.image(img_url, width=100)
                            elif 'href' in first_photo:
                                st.image(first_photo['href'], width=100)
                    except Exception as e:
                        pass
                
                st.markdown("---")
        
        # Simple stats
        st.info(f"📊 Total: {len(st.session_state.drafts)} drafts")
else:
    st.info("👆 Enter your API Key to view your drafts")

# Instructions and troubleshooting
st.markdown("---")
with st.expander("ℹ️ How to use & Troubleshooting"):
    st.markdown("""
    ### 📌 How to use:
    1. **Get your API Key** from [Reverb Developers](https://reverb.com/developers)
    2. Make sure your API key has **write permissions**
    3. Enter your API Key above
    4. Click **"Load My Drafts"** to see all your drafts
    5. Use **Publish** button to publish any draft
    
    ### 🔧 Troubleshooting 404 Error:
    - **First click "Details"** to check the listing status
    - Make sure the listing is complete (has photos, price, etc.)
    - Some listings need to be completed before publishing
    - Try publishing from the Reverb website first to see if it works there
    
    ### ✅ What this tool does:
    - Shows all your drafts from Reverb
    - One-click publish (when possible)
    - Delete drafts you don't need
    """)

st.markdown("---")
st.markdown("Made with 🎸 | Simple Reverb Draft Manager v2.0")
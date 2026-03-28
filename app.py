import streamlit as st
import requests
import json
import time
from typing import Any, Dict, List, Optional, Tuple

# Page configuration
st.set_page_config(page_title="Reverb Draft Manager", page_icon="📋", layout="centered")
st.title("📋 Reverb Draft Manager - Fixed Version")
st.markdown("---")

API_BASE = "https://api.reverb.com/api"
PER_PAGE = 50
MAX_PAGES = 20
SAFE_PUBLISH_DELAY_SECONDS = 1.5

def build_headers(api_key: str, include_content_type: bool = True) -> Dict[str, str]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept-Version": "3.0",
    }
    if include_content_type:
        headers["Content-Type"] = "application/json"
    return headers


def get_my_drafts(api_key: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """Fetch all drafts from my account (all pages)."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept-Version": "3.0",
        "Content-Type": "application/json"
    }
    
    try:
        all_drafts: List[Dict[str, Any]] = []
        page = 1

        while page <= MAX_PAGES:
            response = requests.get(
                f"{API_BASE}/my/listings",
                headers=headers,
                params={"state": "draft", "per_page": PER_PAGE, "page": page},
                timeout=15
            )

            if response.status_code != 200:
                return None, f"Error fetching drafts: {response.status_code} - {response.text[:120]}"

            data = response.json()

            if isinstance(data, dict) and "listings" in data:
                page_drafts = data.get("listings", [])
            elif isinstance(data, list):
                page_drafts = data
            else:
                page_drafts = []

            if not page_drafts:
                break

            all_drafts.extend(page_drafts)

            if len(page_drafts) < PER_PAGE:
                break
            page += 1

        return all_drafts, None
            
    except Exception as e:
        return None, str(e)

def publish_draft(api_key: str, listing_id: Any) -> Tuple[bool, str]:
    """Publish a draft listing."""
    headers = build_headers(api_key)
    
    # Try different possible publish endpoints
    endpoints_to_try = [
        f"{API_BASE}/listings/{listing_id}/publish",
        f"{API_BASE}/my/listings/{listing_id}/publish",
        f"{API_BASE}/listings/{listing_id}/state/publish",
        f"{API_BASE}/my/listings/{listing_id}/state/publish"
    ]
    
    for endpoint in endpoints_to_try:
        try:
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


def is_listing_publish_ready(draft: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Best-effort preflight checks so we only attempt professional/safe publishing."""
    issues = []

    title = str(draft.get("title", "")).strip()
    if len(title) < 5:
        issues.append("Title too short")

    photos = draft.get("photos", [])
    if not isinstance(photos, list) or len(photos) == 0:
        issues.append("Missing photos")

    price_data = draft.get("price", {})
    amount = None
    if isinstance(price_data, dict):
        amount = price_data.get("amount")
    elif price_data is not None:
        amount = price_data
    try:
        if float(amount) <= 0:
            issues.append("Invalid price")
    except Exception:
        issues.append("Invalid price")

    return len(issues) == 0, issues


def publish_all_drafts_safely(api_key: str, drafts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Publish all publish-ready drafts with a short delay.
    This helps avoid aggressive burst behavior and surfaces actionable errors.
    """
    results = {
        "published": [],
        "skipped": [],
        "failed": []
    }

    for draft in drafts:
        listing_id = draft.get("id")
        title = draft.get("title", "Untitled")

        ready, issues = is_listing_publish_ready(draft)
        if not ready:
            results["skipped"].append({"id": listing_id, "title": title, "issues": issues})
            continue

        success, message = publish_draft(api_key, listing_id)
        if success:
            results["published"].append({"id": listing_id, "title": title, "message": message})
        else:
            results["failed"].append({"id": listing_id, "title": title, "message": message})

        time.sleep(SAFE_PUBLISH_DELAY_SECONDS)

    return results

def delete_draft(api_key: str, listing_id: Any) -> Tuple[bool, str]:
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

def check_listing_details(api_key: str, listing_id: Any) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Get detailed information about a listing"""
    headers = build_headers(api_key, include_content_type=False)
    
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
    col1, col2, col3 = st.columns(3)
    
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

    with col3:
        if st.button("🚀 Publish All (Safe)", use_container_width=True):
            if 'drafts' not in st.session_state:
                st.warning("Load drafts first, then publish all.")
            elif not st.session_state.drafts:
                st.info("No drafts to publish.")
            else:
                with st.spinner("Publishing all eligible drafts safely..."):
                    batch_results = publish_all_drafts_safely(api_key, st.session_state.drafts)

                    published_count = len(batch_results["published"])
                    skipped_count = len(batch_results["skipped"])
                    failed_count = len(batch_results["failed"])

                    st.success(f"Published: {published_count}")
                    if skipped_count:
                        st.warning(f"Skipped (not publish-ready): {skipped_count}")
                    if failed_count:
                        st.error(f"Failed: {failed_count}")

                    if batch_results["skipped"]:
                        with st.expander("Skipped drafts details"):
                            for item in batch_results["skipped"]:
                                st.write(f"- `{item['id']}` {item['title']}: {', '.join(item['issues'])}")

                    if batch_results["failed"]:
                        with st.expander("Failed drafts details"):
                            for item in batch_results["failed"]:
                                st.write(f"- `{item['id']}` {item['title']}: {item['message']}")

                    drafts, error = get_my_drafts(api_key)
                    if not error:
                        st.session_state.drafts = drafts
    
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
                    ready, issues = is_listing_publish_ready(draft)
                    st.write(f"📌 Status: {state}")
                    st.write(f"✅ Publish-ready: {'Yes' if ready else 'No'}")
                    if not ready:
                        st.caption(f"Needs: {', '.join(issues)}")
                
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
    5. Use **Publish** to publish one draft, or **Publish All (Safe)** to publish every publish-ready draft in one click
    
    ### 🔧 Troubleshooting 404 Error:
    - **First click "Details"** to check the listing status
    - Make sure the listing is complete (has photos, price, etc.)
    - Some listings need to be completed before publishing
    - Try publishing from the Reverb website first to see if it works there
    
    ### ✅ What this tool does:
    - Shows all your drafts from Reverb (paged)
    - One-click publish per listing
    - One-click **safe batch publishing** with preflight checks and pacing
    - Delete drafts you don't need
    """)

st.markdown("---")
st.markdown("Made with 🎸 | Simple Reverb Draft Manager v2.0")

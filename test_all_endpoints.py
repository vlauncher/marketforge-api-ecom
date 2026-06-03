import httpx
import json
import re

BASE_URL = "http://127.0.0.1:8000"

def get_token():
    # Register and login to get a valid token for protected routes
    httpx.post(f"{BASE_URL}/auth/register", json={"email": "testall@example.com", "password": "SecurePass123!"})
    resp = httpx.post(f"{BASE_URL}/auth/login", json={"email": "testall@example.com", "password": "SecurePass123!"})
    return resp.json().get("access_token")

def main():
    # 1. Fetch OpenAPI schema
    resp = httpx.get(f"{BASE_URL}/openapi.json")
    schema = resp.json()
    
    paths = schema.get("paths", {})
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    total_endpoints = 0
    success_count = 0
    errors = []

    print(f"Found {len(paths)} unique paths. Testing endpoints...\n")

    for path, methods in paths.items():
        for method in methods.keys():
            if method.lower() in ["get", "post", "put", "patch", "delete"]:
                total_endpoints += 1
                
                # Replace path parameters with dummy values for testing
                test_path = re.sub(r'\{[^}]+\}', '1', path)
                test_path = re.sub(r'\{[^}]+_slug\}', 'test-slug', test_path)
                
                url = f"{BASE_URL}{test_path}"
                
                try:
                    if method.lower() == "get":
                        r = httpx.get(url, headers=headers, timeout=5.0)
                    elif method.lower() == "post":
                        r = httpx.post(url, headers=headers, json={}, timeout=5.0)
                    elif method.lower() == "put":
                        r = httpx.put(url, headers=headers, json={}, timeout=5.0)
                    elif method.lower() == "patch":
                        r = httpx.patch(url, headers=headers, json={}, timeout=5.0)
                    elif method.lower() == "delete":
                        r = httpx.delete(url, headers=headers, timeout=5.0)
                    
                    # 4xx errors are expected (auth, validation, not found). 5xx is a real failure.
                    if r.status_code >= 500:
                        errors.append(f"{method.upper()} {path} -> {r.status_code} {r.text[:100]}")
                    else:
                        success_count += 1
                        
                except httpx.RequestError as e:
                    errors.append(f"{method.upper()} {path} -> Request Error: {e}")

    print(f"--- Results ---")
    print(f"Total endpoints tested: {total_endpoints}")
    print(f"Successfully handled (2xx, 3xx, 4xx): {success_count}")
    
    if errors:
        print(f"\n⚠️ Found {len(errors)} endpoints returning 5xx errors or crashing:")
        for err in errors:
            print(f"  - {err}")
    else:
        print("\n✅ All endpoints are responding correctly! No 500 Internal Server Errors found.")

if __name__ == "__main__":
    main()

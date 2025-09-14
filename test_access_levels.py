#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست سطوح دسترسی سیستم مدیریت وام و خریداران

این اسکریپت API endpoints مختلف را با نقش‌های مختلف کاربری تست می‌کند
تا اطمینان حاصل شود که سطح دسترسی‌ها درست کار می‌کنند.
"""

import requests
import json
from typing import Dict, Any, Optional

# API Base URL
BASE_URL = "http://127.0.0.1:5000"

def login_user(national_id: str, password: str) -> Optional[Dict[str, Any]]:
    """Login user and return user info + token"""
    try:
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "national_id": national_id,
            "password": password
        })
        data = response.json()
        if data.get("status") == "success":
            return {
                "role": data.get("role"),
                "display_name": data.get("display_name"),
                "token": data.get("token")
            }
        else:
            print(f"❌ Login failed for {national_id}: {data.get('message')}")
            return None
    except Exception as e:
        print(f"❌ Login error for {national_id}: {e}")
        return None

def test_endpoint(url: str, token: str, method: str = "GET", data: Optional[Dict] = None) -> Dict[str, Any]:
    """Test an API endpoint with given token"""
    headers = {"X-Auth-Token": token} if token else {}
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data or {})
        elif method == "PATCH":
            response = requests.patch(url, headers=headers, json=data or {})
        elif method == "DELETE":
            response = requests.delete(url, headers=headers)
        
        return {
            "status_code": response.status_code,
            "data": response.json() if response.content else {},
            "success": response.status_code < 400
        }
    except Exception as e:
        return {
            "status_code": 0,
            "data": {"error": str(e)},
            "success": False
        }

def run_access_tests():
    """اجرای تست‌های سطح دسترسی"""
    
    print("🚀 شروع تست سطوح دسترسی سیستم")
    print("=" * 60)
    
    # نیاز به اطلاعات کاربران موجود - این بخش را بر اساس کاربران واقعی تنظیم کنید
    test_users = [
        {"national_id": "1234567890", "password": "admin123", "expected_role": "admin"},
        {"national_id": "0987654321", "password": "user123", "expected_role": "employee"}
    ]
    
    user_sessions = {}
    
    # 1. تست Login
    print("\n📝 تست ورود کاربران:")
    for user in test_users:
        session = login_user(user["national_id"], user["password"])
        if session:
            user_sessions[user["expected_role"]] = session
            print(f"✅ {user['expected_role']}: {session['display_name']} - {session['role']}")
        else:
            print(f"❌ {user['expected_role']}: ورود ناموفق")
    
    if not user_sessions:
        print("❌ هیچ کاربری وارد نشد. تست متوقف می‌شود.")
        return
    
    # 2. تست دسترسی به وام‌ها
    print("\n💰 تست دسترسی به وام‌ها:")
    
    test_cases = [
        {
            "name": "فهرست وام‌ها",
            "url": f"{BASE_URL}/api/loans",
            "method": "GET",
            "admin_expected": 200,
            "employee_expected": 200,
            "note": "هر دو باید دسترسی داشته باشند اما با داده‌های متفاوت"
        },
        {
            "name": "ایجاد وام جدید",
            "url": f"{BASE_URL}/api/loans",
            "method": "POST",
            "data": {
                "bank_name": "بانک تست",
                "loan_type": "وام مسکن",
                "duration": "10 سال",
                "amount": 1000000,
                "owner_full_name": "تست کننده",
                "owner_phone": "09123456789",
                "loan_status": "available"
            },
            "admin_expected": 200,
            "employee_expected": 403,
            "note": "فقط ادمین باید بتواند وام ایجاد کند"
        }
    ]
    
    for test in test_cases:
        print(f"\n🔍 تست: {test['name']}")
        
        # تست با ادمین
        if "admin" in user_sessions:
            admin_token = user_sessions["admin"]["token"]
            result = test_endpoint(test["url"], admin_token, test["method"], test.get("data"))
            expected = test["admin_expected"]
            status = "✅" if result["status_code"] == expected else "❌"
            print(f"  {status} ادمین: {result['status_code']} (انتظار: {expected})")
            
        # تست با کارمند
        if "employee" in user_sessions:
            emp_token = user_sessions["employee"]["token"]
            result = test_endpoint(test["url"], emp_token, test["method"], test.get("data"))
            expected = test["employee_expected"]
            status = "✅" if result["status_code"] == expected else "❌"
            print(f"  {status} کارمند: {result['status_code']} (انتظار: {expected})")
        
        print(f"  📝 توضیح: {test['note']}")
    
    # 3. تست دسترسی به خریداران وام
    print("\n👥 تست دسترسی به خریداران وام:")
    
    buyer_tests = [
        {
            "name": "فهرست خریداران",
            "url": f"{BASE_URL}/api/loan-buyers",
            "method": "GET",
            "admin_expected": 200,
            "employee_expected": 200,
            "note": "هر دو دسترسی دارند اما ادمین همه را می‌بیند، کارمند فقط خودش"
        },
        {
            "name": "ایجاد خریدار جدید",
            "url": f"{BASE_URL}/api/loan-buyers",
            "method": "POST",
            "data": {
                "first_name": "تست",
                "last_name": "کننده",
                "national_id": "9876543210",
                "phone": "09123456789",
                "requested_amount": 500000,
                "processing_status": "request_registered"
            },
            "admin_expected": 200,
            "employee_expected": 200,
            "note": "هر دو باید بتوانند خریدار ایجاد کنند"
        }
    ]
    
    for test in buyer_tests:
        print(f"\n🔍 تست: {test['name']}")
        
        # تست با ادمین
        if "admin" in user_sessions:
            admin_token = user_sessions["admin"]["token"]
            result = test_endpoint(test["url"], admin_token, test["method"], test.get("data"))
            expected = test["admin_expected"]
            status = "✅" if result["status_code"] == expected else "❌"
            print(f"  {status} ادمین: {result['status_code']} (انتظار: {expected})")
            
        # تست با کارمند
        if "employee" in user_sessions:
            emp_token = user_sessions["employee"]["token"]
            result = test_endpoint(test["url"], emp_token, test["method"], test.get("data"))
            expected = test["employee_expected"]
            status = "✅" if result["status_code"] == expected else "❌"
            print(f"  {status} کارمند: {result['status_code']} (انتظار: {expected})")
        
        print(f"  📝 توضیح: {test['note']}")
    
    # 4. تست endpoints مخصوص ادمین
    print("\n🔒 تست endpoints مخصوص ادمین:")
    
    admin_only_tests = [
        {
            "name": "مدیریت کارمندان",
            "url": f"{BASE_URL}/api/employees",
            "method": "GET"
        },
        {
            "name": "گزارش مالی",
            "url": f"{BASE_URL}/api/finance/metrics",
            "method": "GET"
        },
        {
            "name": "گزارش فعالیت",
            "url": f"{BASE_URL}/api/activity",
            "method": "GET"
        }
    ]
    
    for test in admin_only_tests:
        print(f"\n🔍 تست: {test['name']}")
        
        # تست با ادمین
        if "admin" in user_sessions:
            admin_token = user_sessions["admin"]["token"]
            result = test_endpoint(test["url"], admin_token, test["method"])
            status = "✅" if result["success"] else "❌"
            print(f"  {status} ادمین: {result['status_code']}")
            
        # تست با کارمند
        if "employee" in user_sessions:
            emp_token = user_sessions["employee"]["token"]
            result = test_endpoint(test["url"], emp_token, test["method"])
            status = "✅" if result["status_code"] == 403 else "❌"
            print(f"  {status} کارمند: {result['status_code']} (انتظار: 403 - ممنوع)")
    
    print("\n" + "=" * 60)
    print("🏁 تست‌ها تمام شد!")
    print("\nنتایج:")
    print("✅ = تست موفق")
    print("❌ = تست ناموفق")
    print("\n💡 نکته: برای اجرای کامل تست‌ها، ابتدا کاربران مورد نیاز را در سیستم ایجاد کنید.")

if __name__ == "__main__":
    run_access_tests()
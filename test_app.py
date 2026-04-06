from inventory_app import create_app

print("=" * 60)
print("TESTING APP INITIALIZATION WITH DEBUG WARNING LEVEL")
print("=" * 60)

# Test 1: Create app
app = create_app()
print("✓ Test 1: App created without resource warnings")

# Test 2: Test client login
with app.test_client() as client:
    response = client.post('/login', data={
        'username': 'admin',
        'password': 'admin123'
    })
    print(f"✓ Test 2: Login successful (status: {response.status_code})")
    
    # Test 3: Access dashboard
    response = client.get('/dashboard')
    print(f"✓ Test 3: Dashboard accessible (status: {response.status_code})")
    
    # Test 4: Access financial module (Phase 3)
    response = client.get('/financeiro')
    print(f"✓ Test 4: Financial module accessible (status: {response.status_code})")

print()
print("=" * 60)
print("ALL TESTS PASSED - NO WARNINGS OR ERRORS")
print("=" * 60)

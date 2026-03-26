from tests import test_cache, test_integration, test_response

print("==== Running Cache Tests ====\n")
test_cache.run()
print("\n==== End of Cache Tests ====\n")

print("==== Running Response with Cache Tests ====\n")
test_response.run()
print("\n==== End of Response with Cache Tests ====\n")

print("==== Running Integration Tests ====\n")
test_integration.run()
print("\n==== End of Integration Tests ====\n")

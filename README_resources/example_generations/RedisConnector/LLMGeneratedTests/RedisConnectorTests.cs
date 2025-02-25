using System;
using Moq;
using MyCompany.ExternalLibraries.Redis;
using StackExchange.Redis;
using Xunit;

namespace MyCompany.ExternalLibraries.Tests.Redis
{
    // Test subclass that overrides the connection method to allow injecting a mocked IConnectionMultiplexer
    public class TestableRedisConnector : RedisConnector
    {
        private readonly IConnectionMultiplexer _connectionMultiplexer;

        public TestableRedisConnector(IConnectionMultiplexer connectionMultiplexer)
        {
            _connectionMultiplexer = connectionMultiplexer;
        }

        // Override to return the injected IConnectionMultiplexer instead of creating a new connection
        protected override IConnectionMultiplexer GetConnectionMultiplexer(string connectionString)
        {
            return _connectionMultiplexer;
        }
    }

    public class RedisConnectorTests
    {
        // Test when the key exists in Redis
        [Fact]
        public void GetKeyValue_KeyExists_ReturnsValue()
        {
            // Arrange
            // Set the SECURE_GATEWAY environment variable needed by the implementation
            Environment.SetEnvironmentVariable("SECURE_GATEWAY", "testgateway");

            // Create a mock for IDatabase
            var dbMock = new Mock<IDatabase>();
            string testKey = "myKey";
            string expectedValue = "myValue";

            // Set up the mock to return the expected value when StringGet is called with 'myKey'
            dbMock
                .Setup(db => db.StringGet(testKey, It.IsAny<CommandFlags>()))
                .Returns(expectedValue);

            // Create a mock for IConnectionMultiplexer
            var multiplexerMock = new Mock<IConnectionMultiplexer>();
            // Set up GetDatabase() to return the mocked IDatabase
            multiplexerMock
                .Setup(m => m.GetDatabase(It.IsAny<int>(), It.IsAny<object>()))
                .Returns(dbMock.Object);

            // Use the testable connector that returns the mocked multiplexer
            IRedisConnector connector = new TestableRedisConnector(multiplexerMock.Object);

            // Act
            string actualValue = connector.GetKeyValue("dummyPassword", testKey);

            // Assert
            Assert.Equal(expectedValue, actualValue);

            // Verify that GetDatabase was called on the connection multiplexer
            multiplexerMock.Verify(
                m => m.GetDatabase(It.IsAny<int>(), It.IsAny<object>()),
                Times.Once
            );
        }

        // Test when the key does not exist in Redis
        [Fact]
        public void GetKeyValue_KeyDoesNotExist_ReturnsNull()
        {
            // Arrange
            Environment.SetEnvironmentVariable("SECURE_GATEWAY", "testgateway");

            var dbMock = new Mock<IDatabase>();
            string testKey = "nonexistentKey";

            // Setup the mock to return an empty RedisValue when the key does not exist
            dbMock
                .Setup(db => db.StringGet(testKey, It.IsAny<CommandFlags>()))
                .Returns(RedisValue.Null);

            var multiplexerMock = new Mock<IConnectionMultiplexer>();
            multiplexerMock
                .Setup(m => m.GetDatabase(It.IsAny<int>(), It.IsAny<object>()))
                .Returns(dbMock.Object);

            IRedisConnector connector = new TestableRedisConnector(multiplexerMock.Object);

            // Act
            string actualValue = connector.GetKeyValue("dummyPassword", testKey);

            // Assert
            Assert.Null(actualValue);
        }
    }
}

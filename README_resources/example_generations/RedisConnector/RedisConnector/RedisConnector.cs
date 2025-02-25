using System;
using OutSystems.ExternalLibraries.SDK;
using StackExchange.Redis;

namespace MyCompany.ExternalLibraries.Redis
{
    // Expose the interface as an external library using the OSInterface attribute
    [OSInterface(
        Name = "RedisConnector",
        Description = "Connects to a Redis instance via the secure gateway and retrieves a key value",
        IconResourceName = "RedisConnector.icon.png"
    )]
    public interface IRedisConnector
    {
        // Expose the GetKeyValue method as a server action
        [OSAction(
            Description = "Retrieves the value for the specified key from Redis",
            ReturnName = "RedisValue",
            ReturnDescription = "Value associated with the key in Redis",
            ReturnType = OSDataType.Text
        )]
        string GetKeyValue(
            [OSParameter(
                Description = "Password for the Redis database",
                DataType = OSDataType.Text
            )]
                string password,
            [OSParameter(
                Description = "The key whose value to retrieve",
                DataType = OSDataType.Text
            )]
                string key
        );
    }

    // Implementation of the IRedisConnector interface
    public class RedisConnector : IRedisConnector
    {
        // This method connects to Redis using the provided connection string. It is virtual to allow overriding in tests.
        protected virtual IConnectionMultiplexer GetConnectionMultiplexer(string connectionString)
        {
            return ConnectionMultiplexer.Connect(connectionString);
        }

        // Connects to a Redis instance via a secure gateway and retrieves the value for the provided key.
        public string GetKeyValue(string password, string key)
        {
            // Retrieve the secure gateway hostname from the environment variable
            string secureGateway =
                Environment.GetEnvironmentVariable("SECURE_GATEWAY")
                ?? throw new Exception("SECURE_GATEWAY environment variable is not set");

            // Construct the Redis connection string. Format: "hostname:port,password=yourPassword"
            string connectionString = $"{secureGateway}:6379,password={password}";

            // Connect to Redis using the connection multiplexer
            using (IConnectionMultiplexer redis = GetConnectionMultiplexer(connectionString))
            {
                // Retrieve the default database
                IDatabase db = redis.GetDatabase();

                // Fetch the value for the specified key from Redis
                RedisValue redisValue = db.StringGet(key);

                // If the key does not exist, return null; otherwise return the value as a string
                return redisValue.HasValue ? redisValue.ToString() : null;
            }
        }
    }
}

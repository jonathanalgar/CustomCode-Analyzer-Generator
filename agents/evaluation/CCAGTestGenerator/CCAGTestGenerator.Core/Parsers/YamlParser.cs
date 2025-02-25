using CCAGTestGenerator.Core.Models;
using YamlDotNet.Serialization;
using YamlDotNet.Serialization.NamingConventions;

namespace CCAGTestGenerator.Core.Parsers
{
    public static class YamlParser
    {
        /// <summary>
        /// Deserializes the YAML content into <see cref="YamlSpec"/>, which contains the
        /// description, dictionary of actions, and so forth.
        /// </summary>
        /// <param name="yamlContent">The YAML string to parse.</param>
        /// <returns>A <see cref="YamlSpec"/> object representing the YAML structure.</returns>
        public static YamlSpec Parse(string yamlContent)
        {
            var deserializer = new DeserializerBuilder()
                .WithNamingConvention(CamelCaseNamingConvention.Instance)
                .Build();
            return deserializer.Deserialize<YamlSpec>(yamlContent);
        }
    }
}

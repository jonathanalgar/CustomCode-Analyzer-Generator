namespace CCAGTestGenerator.Core.Models
{
    /// <summary>
    /// Represents a single YAML test case, including parameter inputs and the expected output.
    /// </summary>
    public class YamlTestCase
    {
        public required Dictionary<string, object> Inputs { get; set; }
        public required object Expected { get; set; }
    }

    /// <summary>
    /// Describes a single YAML action block, containing the list of parameter names
    /// and one or more test cases for that action.
    /// </summary>
    public class YamlAction
    {
        public required List<string> Params { get; set; }
        public required List<YamlTestCase> TestCases { get; set; }
    }

    /// <summary>
    /// Represents the top-level YAML specification object, which includes a description
    /// and a collection of named actions.
    /// </summary>
    public class YamlSpec
    {
        public required string Description { get; set; }
        public required Dictionary<string, YamlAction> Actions { get; set; }
    }
}

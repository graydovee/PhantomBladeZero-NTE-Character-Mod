using UnrealBuildTool;

public class ProjectPBZEditor : ModuleRules
{
	public ProjectPBZEditor(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		PublicDependencyModuleNames.AddRange(new string[]
		{
			"Core",
			"CoreUObject",
			"Engine",
			"UnrealEd"
		});
	}
}

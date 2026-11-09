#include "CoreMinimal.h"
#include "Modules/ModuleManager.h"

class FProjectPBZEditorModule : public IModuleInterface
{
public:
	virtual void StartupModule() override {}
	virtual void ShutdownModule() override {}
};

IMPLEMENT_MODULE(FProjectPBZEditorModule, ProjectPBZEditor);

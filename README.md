Sprout
-----

A template for MCDReforged (>=2.x) plugin, included in Project Blooming Blossom

Try `python -m mcdreforged pack` to generate the packed plugin!

This template is licensed under MIT license.



## 插件功能

##### !!tpa: 向其他玩家发送传送请求，同意后即可传送至对方身边

```
!!tpa						接受其他玩家的传送请求
!!tpa <玩家>					向指定玩家发送传送请求
```



##### !!home: 在你的世界中标记一处地点，可随时返回已标记地点

```
!!home <门牌号>				回到指定的家
!!home add <门牌号>			添加玩家当前位置作为家	
!!home remove <门牌号>			删除指定家
!! home list				列出你所有的家
```



##### !!back: 撤销上一次传送，返回传送前的位置（仅适用于本插件发生的传送）

```
!!back 						返回传送前的位置
```



## Feature

##### !!tpa: Send a teleport request to other players, and once accepted, you will be teleported to their location.

```
!!tpa Accept				teleport requests from other players
!!tpa <player>				Send a teleport request to the specified player
```

##### !!home: Save player's position as home, and you can teleport to the saved home at any time.

```
!!home <home>				Return to the specified home
!!home add <home>			Add the player's current location as a home
!!home remove <home>		Delete the specified home
!!home list					List all currently owned homes
```

##### !!back: Undo the last teleport and return to the position before the last teleport (only applicable to teleports made by this plugin).

```
!!back 						Return to the position before the last teleport
```

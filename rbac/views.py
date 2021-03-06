from django.shortcuts import render, HttpResponse, redirect
from rbac import models
import re

# Create your views here.

'''
def menu_content(result):
    response = ""
    tpl = """
    <div class="item %s">
        <div class = "title">%s</div>
        <div class = "content">%s</div>
    </div>
    """
    for row in result:
        if not row['status']:
            continue
        active = ""
        if row['open']:
            active = "active"
        if 'url' in row:
            response += "<a class='%s' href=%s>%s</a>" %(active, row['url'], row['caption'])
        else:
            title = row['caption']
            content = menu_content(row['child'])
            response += tpl %(active, title, content)
    return response


def menu_tree(result):

    response = ""
    tpl = """
    <div class="item %s">
        <div class = "title">%s</div>
        <div class = "content">%s</div>
    </div>
    """
    for row in result:
        if not row['status']:
            continue
        active = ""
        if row['open']:
            active = "active"

        # 第一层第一个
        title = row['caption']
        # 第一层第一个的后代
        content = menu_content(row['child'])
        response += tpl %(active, title, content)

    return response


def report(request):
    user_request_url = '/report.html'
    username = request.GET.get('u')

    role_list = models.Role.objects.filter(user2role__u__username=username)
###########################################################################
    # user_obj = models.User.objects.filter(username=username)
    #方式一
    #通过manytomany方式生成的第三张表
    #m  manytomany
    #role_list = user_obj.m.all()

    #方式二
    #自建的第三张表
    #user2role_list = models.User2Role.objects.filter(u=user_obj)  #[user2role 的对象]

    #方式三
    #role_list = models.Role.objects.filter(user2role__u=user_obj)
    #print(role_list)

    #方式四
    #role_list = models.Role.objects.filter(user2role__u__username=username)
    # print(role_list)

    # vlist = models.Permission2Action2Role.objects.filter(r__in=role_list)
    #

    #获取个人的所有权限列表，放置在session中，无法获取实时权限信息，需要重新登录
    #permission2action_list = models.Permission2Action.objects.filter(permission2action2role__r__in=role_list).values(
    #    'p__url',
    #    'a__code'
    #).distinct()
    # for item in permission2action_list:
    #     print(item)


    #查看到有权限的url
    # url_list = models.Permission2Action.objects.filter(permission2action2role__r__in=role_list).values(
    #     'p__url',
    #     'p__caption'
    # ).distinct()
    # for item in url_list:
    #     print(item)
###########################################################################


    open_leaf_parent_id = None
    #应该在菜单中显示的权限 --最后一层
    menu_leaf_list = models.Permission2Action.objects. \
        filter(permission2action2role__r__in=role_list).exclude(p__menu__isnull=True). \
        values('p_id','p__url', 'p__caption','p__menu').distinct()
    menu_leaf_dict = {}
    for item in menu_leaf_list:
        # {'p__menu': 4, 'p__url': '/report.html', 'p__caption': '报表管理'}
        item = {
            'id': item['p_id'],
            'url': item['p__url'],
            'caption': item['p__caption'],
            'parent_id': item['p__menu'],
            'child': [],
            'status': True,
            'open': False
        }
        if item['parent_id'] in menu_leaf_dict:
            menu_leaf_dict[item['parent_id']].append(item)
        else:
            menu_leaf_dict[item['parent_id']] = [item, ]

        if re.match(item['url'], user_request_url):
            item['open'] = True
            open_leaf_parent_id = item['parent_id']


    menu_list = models.Menu.objects.values('id','caption','parent_id')
    menu_dict = {}
    for item in menu_list:
        item['child'] = []
        item['status'] = False
        item['open'] = False
        menu_dict[item['id']] = item

    for k, v in menu_leaf_dict.items():
        menu_dict[k]['child'] = v
        parent_id = k
        while parent_id:
            menu_dict[parent_id]['status'] = True
            parent_id = menu_dict[parent_id]['parent_id']

    while open_leaf_parent_id:
        menu_dict[open_leaf_parent_id]['open'] = True
        open_leaf_parent_id = menu_dict[open_leaf_parent_id]['parent_id']


    # 处理等级关系
    #　menu_dict: 应用：评论（models.xx.objects.values('...')）
    result = []
    for row in menu_dict.values():
        if not row['parent_id']:
            result.append(row)
        else:
            menu_dict[row['parent_id']]['child'].append(row)

    # for row in result:
    #     print(row)

    string = menu_tree(result)
    return render(request, 'index.html', {'menu_string': string})
'''


class MenuHelper(object):

    def __init__(self,request,username):
        # 当前请求的request对象
        self.request = request
        # 当前用户名
        self.username = username
        # 获取当前URL
        self.current_url = request.path_info

        # 获取当前用户的所有权限
        self.permission2action_dict = None
        # 获取在菜单中显示的权限
        self.menu_leaf_list = None
        # 获取所有菜单
        self.menu_list = None

        self.session_data()

    def session_data(self):
        permission_dict = self.request.session.get('permission_info')
        if permission_dict:
            self.permission2action_dict = permission_dict['permission2action_dict']
            self.menu_leaf_list = permission_dict['menu_leaf_list']
            self.menu_list = permission_dict['menu_list']
        else:
            # 获取当前用户的角色列表
            role_list = models.Role.objects.filter(user2role__u__username=self.username)

            # 获取当前用户的权限列表（URL+Action）
            # v = [
            #     {'url':'/inde.html','code':'GET'},
            #     {'url':'/inde.html','code':'POST'},
            #     {'url':'/order.html','code':'PUT'},
            #     {'url':'/order.html','code':'GET'},
            # ]
            # v = {
            #     '/inde.html':['GET']
            # }
            permission2action_list = models.Permission2Action.objects. \
                filter(permission2action2role__r__in=role_list). \
                values('p__url', 'a__code').distinct()

            permission2action_dict={}
            for item in permission2action_list:
                if item['p__url'] in permission2action_dict:
                    permission2action_dict[item['p__url']].append(item['a__code'])
                else:
                    permission2action_dict[item['p__url']] = [item['a__code'],]

            # 获取菜单的叶子节点，即：菜单的最后一层应该显示的权限
            menu_leaf_list = list(models.Permission2Action.objects. \
                filter(permission2action2role__r__in=role_list).exclude(p__menu__isnull=True). \
                values('p_id', 'p__url', 'p__caption', 'p__menu').distinct())

            # 获取所有的菜单列表
            menu_list = list(models.Menu.objects.values('id', 'caption', 'parent_id'))

            self.request.session['permission_info'] = {
                'permission2action_dict': permission2action_dict,
                'menu_leaf_list': menu_leaf_list,
                'menu_list': menu_list,
            }

            # self.permission2action_list = permission2action_list
            # self.menu_leaf_list = menu_leaf_list
            # self.menu_list = menu_list

    def menu_data_list(self):

        menu_leaf_dict = {}
        open_leaf_parent_id = None

        # 归并所有的叶子节点
        for item in self.menu_leaf_list:
            item = {
                'id': item['p_id'],
                'url': item['p__url'],
                'caption': item['p__caption'],
                'parent_id': item['p__menu'],
                'child': [],
                'status': True,  # 是否显示
                'open': False
            }
            if item['parent_id'] in menu_leaf_dict:
                menu_leaf_dict[item['parent_id']].append(item)
            else:
                menu_leaf_dict[item['parent_id']] = [item, ]
            if re.match(item['url'], self.current_url):
                item['open'] = True
                open_leaf_parent_id = item['parent_id']

        # 获取所有菜单字典
        menu_dict = {}
        for item in self.menu_list:
            item['child'] = []
            item['status'] = False
            item['open'] = False
            menu_dict[item['id']] = item

        # 讲叶子节点添加到菜单中
        for k, v in menu_leaf_dict.items():
            menu_dict[k]['child'] = v
            parent_id = k
            # 将后代中有叶子节点的菜单标记为【显示】
            while parent_id:
                menu_dict[parent_id]['status'] = True
                parent_id = menu_dict[parent_id]['parent_id']

        # 将已经选中的菜单标记为【展开】
        while open_leaf_parent_id:
            menu_dict[open_leaf_parent_id]['open'] = True
            open_leaf_parent_id = menu_dict[open_leaf_parent_id]['parent_id']

        # 生成树形结构数据
        result = []
        for row in menu_dict.values():
            if not row['parent_id']:
                result.append(row)
            else:
                menu_dict[row['parent_id']]['child'].append(row)

        return result

    def menu_content(self,child_list):
        response = ""
        tpl = """
            <div class="item %s">
                <div class="title">%s</div>
                <div class="content">%s</div>
            </div>
        """
        for row in child_list:
            if not row['status']:
                continue
            active = ""
            if row['open']:
                active = "active"
            if 'url' in row:
                response += "<a class='%s' href='%s'>%s</a>" % (active, row['url'], row['caption'])
            else:
                title = row['caption']
                content = self.menu_content(row['child'])
                response += tpl % (active, title, content)
        return response

    def menu_tree(self):
        response = ""
        tpl = """
        <div class="item %s">
            <div class="title">%s</div>
            <div class="content">%s</div>
        </div>
        """
        for row in self.menu_data_list():
            if not row['status']:
                continue
            active = ""
            if row['open']:
                active = "active"
            # 第一层第一个
            title = row['caption']
            # 第一层第一个的后代
            content = self.menu_content(row['child'])
            response += tpl % (active, title, content)
        return response

    def actions(self):
        """
        检查当前用户是否对当前URL有权访问，并获取对当前URL有什么权限
        """
        action_list = []
        # 当前所有权限
        # {
        #     '/index.html': ['GET',POST,]
        # }
        for k,v in self.permission2action_dict.items():
            if re.match(k,self.current_url):
                action_list = v # ['GET',POST,]
                break

        return action_list



def loginout(request):
    request.session.clear()
    return redirect('login.html')


def login(request):
    if request.method == "GET":
        return render(request, 'login.html')
    else:
        username = request.POST.get('username')
        pwd = request.POST.get('pwd')
        obj = models.User.objects.filter(username=username,password=pwd).first()
        if obj:
            #obj.id obj.username
            #当前的用户信息放到session中
            request.session['user_info'] = {'nid':obj.id, 'username': obj.username}
            #获取当前用户的所有权限
            #获取在菜单中显示的权限
            #获取所有菜单
            #放到session中
            MenuHelper(request, obj.username)
            return redirect('index.html')
        else:
            return HttpResponse('账号或密码错误')


def permission(func):
    def inner(request,*args,**kwargs):
        user_info = request.session.get('user_info')
        if not user_info:
            return redirect('/login.html')
        obj = MenuHelper(request, user_info['username'])
        action_list = obj.actions()
        if not action_list:
            return HttpResponse('无权限访问')
        kwargs['menu_string'] = obj.menu_tree()
        kwargs['action_list'] = action_list
        return func(request, *args, **kwargs)
    return inner


@permission
def index(request, *args, **kwargs):
    action_list = kwargs.get('action_list')
    menu_string = kwargs.get('menu_string')
    print(action_list)
    if "GET" in action_list:
        result = models.User.objects.all()
    else:
        result = []
    return render(request,'index.html',{'menu_string':menu_string,'action_list':action_list})



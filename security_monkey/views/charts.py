"""
.. module: security_monkey.views.GuardDutyEventMapPointsList
    :platform: Unix

.. version:: $$VERSION$$
.. moduleauthor:: Pritam D. Gautam <pritam.gautam@nuagedm.com> @nuagedm

"""

from security_monkey import db, rbac
from security_monkey.views import AuthenticatedService
from security_monkey.datastore import (
    Item,
    ItemAudit,
    Account,
    Technology
)
from sqlalchemy.sql.functions import count as sqlcount, sum
from sqlalchemy import over, cast, false, between,select


# Calculates and returns a list of technologies along with
# its percentage and absolute share in total list of vulnerabilities
class VulnerabilitiesByTech(AuthenticatedService):
    decorators = [rbac.allow(['View'], ["GET"])]

    def get(self):
        """
            .. http:get:: /api/1/vulnbytech

            Get a data for displaying Vulnerabilities by Technology Chart

            **Example Request**:

            .. sourcecode:: http

                GET /api/1/items HTTP/1.1
                Host: example.com
                Accept: application/json

            **Example Response**:

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Vary: Accept
                Content-Type: application/json

                {
                    "items": [
                        {
                            "technology": "alb",
                            "count": 34,
                            "percentage": 49.02
                        }
                    ],
                    "total": 144,
                    "page": 1,
                    "auth": {
                        "authenticated": true,
                        "user": "user@example.com"
                    }
                }

            :statuscode 200: no error
            :statuscode 401: Authentication Error. Please Login.
        """

        self.reqparse.add_argument('accounts', type=str, default=None, location='args')
        args = self.reqparse.parse_args()
        for k, v in args.items():
            if not v:
                del args[k]

        # Read more about filtering:
        # https://docs.sqlalchemy.org/en/latest/orm/query.html
        query = Technology.query.with_entities(Technology.name, sqlcount(1))
        query = query.join(Item, Item.tech_id == Technology.id)
        query = query.join(ItemAudit, Item.id == ItemAudit.item_id)
        query = query.filter(ItemAudit.justified == false())
        query = query.filter(ItemAudit.fixed == false())
        query = query.group_by(Technology.name)
        query = query.order_by(Technology.name)

        if 'accounts' in args:
            accounts = args['accounts'].split(',')
            query = query.join((Account, Account.id == Item.account_id))
            query = query.filter(Account.name.in_(accounts))

        items = query.all()

        marshaled_items = []
        if len(items) > 0:
            import pandas as pd
            df = pd.DataFrame.from_dict([{'technology': str(item[0]), 'count': int(item[1])} for item in items])
            df['percentage'] = (df['count']*100/df['count'].sum()).round(2)

            marshaled_items = df.to_dict(orient='records')

        marshaled_dict = {
            'page': 1,
            'total': len(items),
            'count': len(items),
            'auth': self.auth_dict,
            'items': marshaled_items
        }
        return marshaled_dict, 200


# Calculates and returns a count of open ItemAudit items by
# assigned severity bucketed into Low, Medium, and High
class VulnerabilitiesBySeverity(AuthenticatedService):
    decorators = [rbac.allow(['View'], ["GET"])]

    def get(self):
        """
            .. http:get:: /api/1/vulnbyseverity

            Get a count of open ItemAudit records by severity.

            **Example Request**:

            .. sourcecode:: http

                GET /api/1/items HTTP/1.1
                Host: example.com
                Accept: application/json

            **Example Response**:

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Vary: Accept
                Content-Type: application/json

                {
                    "items": [
                        {
                            "high": 21,
                            "medium": 839,
                            "low": 1152
                        }
                    ],
                    "total": 1,
                    "page": 1,
                    "count" 1,
                    "auth": {
                        "authenticated": true,
                        "user": "user@example.com"
                    }
                }

            :statuscode 200: no error
            :statuscode 401: Authentication Error. Please Login.
        """

        self.reqparse.add_argument('accounts', type=str, default=None, location='args')
        args = self.reqparse.parse_args()
        for k, v in args.items():
            if not v:
                del args[k]

        baseQuery = ItemAudit.query.filter(ItemAudit.justified == false())
        baseQuery = baseQuery.filter(ItemAudit.fixed == false())
        if 'accounts' in args:
            accounts = args['accounts'].split(',')
            baseQuery = baseQuery.join((Item, ItemAudit.item_id == Item.id))
            baseQuery = baseQuery.join((Account, Account.id == Item.account_id))
            baseQuery = baseQuery.filter(Account.name.in_(accounts))

        # select count(1) from itemaudit where justified=false and fixed=false and score < 5
        lowQuery = baseQuery.filter(ItemAudit.score < 5)
        # select count(1) from itemaudit where justified=false and fixed=false and score >= 5 and score <=10
        medQuery = baseQuery.filter(between(ItemAudit.score, 5, 10))
        # select count(1) from itemaudit where justified=false and fixed=false and score > 5
        highQuery = baseQuery.filter(ItemAudit.score > 10)

        marshaled_items = [{
            'low':lowQuery.count(),
            'medium':medQuery.count(),
            'high':highQuery.count()
        }]

        marshaled_dict = {
            'page': 1,
            'total': 1,
            'count': 1,
            'auth': self.auth_dict,
            'items': marshaled_items
        }
        return marshaled_dict, 200

